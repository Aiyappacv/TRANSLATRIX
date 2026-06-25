"""
Surya OCR service for TRANSLATRIX PRO.

Routes PDF/image content through the fastest available text path:
  1. Digitally-generated PDFs  -> PyMuPDF embedded text extraction (exact, ~ms)
  2. Scanned PDFs / images     -> Surya 0.20.0 neural OCR (accurate, ~seconds)

Gemini NEVER receives PDF bytes. It receives only the plain text returned
by this service.
"""
from __future__ import annotations

import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# -- Output dataclasses --------------------------------------------------------


@dataclass
class OcrPageResult:
    page: int              # 1-based page number
    text: str              # plain text in reading order
    tables: list           # pre-extracted table structures (may be empty)
    confidence: float      # 0-1; 1.0 for embedded text, ~0.85 for neural OCR
    has_embedded_text: bool


@dataclass
class OcrDocumentResult:
    pages: list            # list[OcrPageResult]
    total_pages: int
    method: str            # "pymupdf_embedded" | "surya_ocr"
    overall_confidence: float
    processing_time_ms: int


# -- Lazy Surya model singleton ------------------------------------------------

_surya_lock = threading.Lock()
_surya_predictor: Any = None


def _get_surya_predictor():
    global _surya_predictor
    if _surya_predictor is not None:
        return _surya_predictor
    with _surya_lock:
        if _surya_predictor is not None:
            return _surya_predictor
        logger.info("surya_model_loading")
        from surya.recognition import RecognitionPredictor
        _surya_predictor = RecognitionPredictor()
        logger.info("surya_model_loaded")
    return _surya_predictor


# -- Helpers -------------------------------------------------------------------

_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    return _HTML_TAG.sub("", html).strip()


def check_pdf_has_embedded_text(pdf_bytes: bytes, min_avg_chars: int = 50) -> bool:
    """Return True if the PDF has enough digitally-embedded text to skip OCR."""
    try:
        import fitz
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                return False
            total = sum(len(page.get_text().strip()) for page in doc)
            return (total / doc.page_count) >= min_avg_chars
    except Exception:
        return False


def _extract_pymupdf_tables(page: Any) -> list:
    """Extract tables from a PyMuPDF page. Returns [] on failure."""
    try:
        finder = page.find_tables()
        tables = []
        for i, table in enumerate(finder.tables):
            all_rows = table.extract()
            if not all_rows:
                continue
            try:
                headers = [str(h) if h is not None else "" for h in table.header.names]
                data_rows = all_rows
            except AttributeError:
                headers = [str(c) if c is not None else "" for c in all_rows[0]]
                data_rows = all_rows[1:]
            tables.append({
                "table_index": i,
                "page": page.number + 1,
                "headers": headers,
                "rows": [[str(c) if c is not None else "" for c in row] for row in data_rows],
            })
        return tables
    except Exception:
        return []


def extract_text_pymupdf(pdf_bytes: bytes) -> OcrDocumentResult:
    """Fast path: embedded text + table extraction for digitally-generated PDFs."""
    import fitz

    t0 = time.monotonic()
    pages = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text").strip()
            tables = _extract_pymupdf_tables(page)
            pages.append(OcrPageResult(
                page=page.number + 1,
                text=text,
                tables=tables,
                confidence=1.0,
                has_embedded_text=True,
            ))

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info("pymupdf_extraction_complete", total_pages=len(pages), elapsed_ms=elapsed_ms)
    return OcrDocumentResult(
        pages=pages,
        total_pages=len(pages),
        method="pymupdf_embedded",
        overall_confidence=1.0 if pages else 0.0,
        processing_time_ms=elapsed_ms,
    )


def _render_single_page(pdf_bytes: bytes, page_idx: int, dpi: int) -> Any:
    """Render one PDF page to a PIL Image using its own fitz handle."""
    import fitz
    from PIL import Image as PILImage

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)


def _render_pages_parallel(pdf_bytes: bytes, indices: list, dpi: int, max_workers: int) -> list:
    """Render a list of page indices to PIL Images in parallel."""
    if len(indices) == 1:
        return [_render_single_page(pdf_bytes, indices[0], dpi)]

    with ThreadPoolExecutor(max_workers=min(max_workers, len(indices))) as executor:
        futures = {executor.submit(_render_single_page, pdf_bytes, idx, dpi): i
                   for i, idx in enumerate(indices)}
        results: dict = {}
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()

    return [results[i] for i in range(len(indices))]


def _surya_page_to_text(page_result: Any) -> str:
    """Convert a Surya PageOCRResult to plain text in reading order."""
    blocks = sorted(
        [b for b in (page_result.blocks or []) if not getattr(b, "skipped", False)],
        key=lambda b: getattr(b, "reading_order", 0),
    )
    return "\n".join(_strip_html(b.html) for b in blocks if getattr(b, "html", None))


def _ocr_with_surya(pdf_bytes: bytes, dpi: int, max_workers: int, batch_size: int) -> list:
    """Run Surya OCR over all PDF pages in memory-bounded batches."""
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        n = doc.page_count

    predictor = _get_surya_predictor()
    all_pages: list = []

    for batch_start in range(0, n, batch_size):
        batch_indices = list(range(batch_start, min(batch_start + batch_size, n)))
        images = _render_pages_parallel(pdf_bytes, batch_indices, dpi, max_workers)

        try:
            results = predictor(images, full_page=True)
            for j, page_result in enumerate(results):
                text = _surya_page_to_text(page_result)
                n_blocks = len([b for b in (page_result.blocks or [])
                                if not getattr(b, "skipped", False)])
                confidence = min(0.95, 0.70 + 0.01 * n_blocks)
                all_pages.append(OcrPageResult(
                    page=batch_start + j + 1,
                    text=text,
                    tables=[],
                    confidence=confidence,
                    has_embedded_text=False,
                ))
        except Exception as exc:
            logger.error("surya_batch_failed", batch_start=batch_start, error=str(exc))
            for j in range(len(batch_indices)):
                all_pages.append(OcrPageResult(
                    page=batch_start + j + 1,
                    text="",
                    tables=[],
                    confidence=0.0,
                    has_embedded_text=False,
                ))
        finally:
            del images

    return all_pages


def ocr_page_batch(pdf_bytes: bytes, page_indices: list, dpi: int, max_workers: int) -> list:
    """OCR a specific set of PDF pages (0-based indices) and return OcrPageResult list.

    Called per-batch by the async orchestrator so progress can be reported after
    each batch without blocking the event loop. Each call is independent — the
    orchestrator assembles results in order after all batches complete.
    """
    images = _render_pages_parallel(pdf_bytes, page_indices, dpi, max_workers)
    try:
        predictor = _get_surya_predictor()
        results = predictor(images, full_page=True)
        page_results = []
        for j, page_result in enumerate(results):
            text = _surya_page_to_text(page_result)
            n_blocks = len([b for b in (page_result.blocks or [])
                            if not getattr(b, "skipped", False)])
            confidence = min(0.95, 0.70 + 0.01 * n_blocks)
            page_results.append(OcrPageResult(
                page=page_indices[j] + 1,  # convert 0-based index to 1-based page number
                text=text,
                tables=[],
                confidence=confidence,
                has_embedded_text=False,
            ))
        return page_results
    except Exception as exc:
        first = page_indices[0] + 1 if page_indices else "?"
        logger.error("ocr_page_batch_failed", first_page=first, error=str(exc))
        return [
            OcrPageResult(page=idx + 1, text="", tables=[], confidence=0.0, has_embedded_text=False)
            for idx in page_indices
        ]
    finally:
        del images


def ocr_document(
    content: bytes,
    *,
    is_pdf: bool = True,
    langs=None,
    max_workers: int = 4,
    dpi: int = 150,
    batch_size: int = 8,
    min_embedded_chars: int = 50,
) -> OcrDocumentResult:
    """OCR a document, auto-routing to the fastest correct path.

    PDFs with embedded text use PyMuPDF (fast, exact).
    Scanned PDFs and images use Surya 0.20.0 neural OCR.

    Args:
        content: Raw file bytes (PDF or image).
        is_pdf: True for PDF, False for an image (PNG/JPG/TIFF/BMP).
        langs: Accepted for API compat; Surya auto-detects language.
        max_workers: Thread count for parallel page rendering (Surya path).
        dpi: Render resolution for PDF-to-image conversion (Surya path only).
        batch_size: Pages per Surya inference call (bounds peak RAM usage).
        min_embedded_chars: Avg chars/page threshold for PyMuPDF fast path.
    """
    t0 = time.monotonic()

    if is_pdf:
        if check_pdf_has_embedded_text(content, min_avg_chars=min_embedded_chars):
            logger.info("surya_ocr_routing", path="pymupdf_embedded")
            return extract_text_pymupdf(content)

        logger.info("surya_ocr_routing", path="surya_neural")
        pages = _ocr_with_surya(content, dpi=dpi, max_workers=max_workers, batch_size=batch_size)
    else:
        from PIL import Image as PILImage
        import io

        logger.info("surya_ocr_routing", path="surya_image")
        predictor = _get_surya_predictor()
        try:
            img = PILImage.open(io.BytesIO(content)).convert("RGB")
            results = predictor([img], full_page=True)
            text = _surya_page_to_text(results[0]) if results else ""
            n_blocks = (len([b for b in (results[0].blocks or [])
                             if not getattr(b, "skipped", False)]) if results else 0)
            pages = [OcrPageResult(
                page=1, text=text, tables=[],
                confidence=min(0.95, 0.70 + 0.01 * n_blocks),
                has_embedded_text=False,
            )]
        except Exception as exc:
            logger.error("surya_image_ocr_failed", error=str(exc))
            pages = [OcrPageResult(page=1, text="", tables=[], confidence=0.0, has_embedded_text=False)]

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    avg_conf = sum(p.confidence for p in pages) / len(pages) if pages else 0.0
    method = "pymupdf_embedded" if (pages and pages[0].has_embedded_text) else "surya_ocr"

    logger.info(
        "ocr_document_complete",
        method=method,
        total_pages=len(pages),
        elapsed_ms=elapsed_ms,
        avg_confidence=round(avg_conf, 3),
    )

    return OcrDocumentResult(
        pages=pages,
        total_pages=len(pages),
        method=method,
        overall_confidence=avg_conf,
        processing_time_ms=elapsed_ms,
    )
