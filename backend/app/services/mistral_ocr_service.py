"""
Mistral OCR service for TRANSLATRIX PRO.

Fallback OCR engine when Surya is not installed.  Uses the Mistral OCR
API (mistral-ocr-latest) to extract text from PDFs and images.

Returns the same OcrPageResult / OcrDocumentResult dataclasses as
surya_ocr_service so the downstream extraction pipeline is unchanged.
"""
from __future__ import annotations

import base64
import mimetypes
import time
from typing import Any, Optional

import structlog

from app.config import settings

# Re-use the same dataclasses so callers don't care which backend ran.
from app.services.surya_ocr_service import OcrPageResult, OcrDocumentResult

logger = structlog.get_logger(__name__)


def _get_client():
    """Lazily build a Mistral client."""
    from mistralai.client import Mistral

    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not configured")
    return Mistral(api_key=api_key)


def _ocr_process(document: dict, pages: Optional[list[int]] = None) -> Any:
    """Call the Mistral OCR endpoint and return the raw response."""
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": settings.MISTRAL_OCR_MODEL or "mistral-ocr-latest",
        "document": document,
    }
    if pages is not None:
        kwargs["pages"] = pages
    return client.ocr.process(**kwargs)


# ---------------------------------------------------------------------------
# Public API — mirrors surya_ocr_service
# ---------------------------------------------------------------------------


def check_pdf_has_embedded_text(pdf_bytes: bytes, min_avg_chars: int = 50) -> bool:
    """Re-exported from surya_ocr_service for convenience."""
    from app.services.surya_ocr_service import check_pdf_has_embedded_text as _check
    return _check(pdf_bytes, min_avg_chars)


def extract_text_pymupdf(pdf_bytes: bytes) -> OcrDocumentResult:
    """Re-exported from surya_ocr_service — PyMuPDF fast path."""
    from app.services.surya_ocr_service import extract_text_pymupdf as _extract
    return _extract(pdf_bytes)


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """Return the page count of a PDF."""
    import fitz
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc.page_count


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
    """OCR a full document via the Mistral OCR API.

    For digitally-generated PDFs, uses the PyMuPDF fast path (same as Surya).
    For scanned PDFs and images, calls the Mistral OCR API.
    """
    t0 = time.monotonic()

    if is_pdf:
        if check_pdf_has_embedded_text(content, min_avg_chars=min_embedded_chars):
            logger.info("mistral_ocr_routing", path="pymupdf_embedded")
            return extract_text_pymupdf(content)

        logger.info("mistral_ocr_routing", path="mistral_api")
        b64 = base64.standard_b64encode(content).decode("ascii")
        document = {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        }
    else:
        logger.info("mistral_ocr_routing", path="mistral_api_image")
        # Guess MIME type from magic bytes
        mime = "image/jpeg"
        if content[:4] == b"\x89PNG":
            mime = "image/png"
        elif content[:4] in (b"II*\x00", b"MM\x00*"):
            mime = "image/tiff"
        b64 = base64.standard_b64encode(content).decode("ascii")
        document = {
            "type": "image_url",
            "image_url": f"data:{mime};base64,{b64}",
        }

    try:
        response = _ocr_process(document)
    except Exception as exc:
        logger.error("mistral_ocr_api_failed", error=str(exc))
        raise RuntimeError(f"Mistral OCR API failed: {exc}") from exc

    pages: list[OcrPageResult] = []
    for i, page in enumerate(response.pages):
        text = page.markdown.strip() if hasattr(page, "markdown") and page.markdown else ""
        pages.append(OcrPageResult(
            page=i + 1,
            text=text,
            tables=[],
            confidence=0.90,
            has_embedded_text=False,
        ))

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    avg_conf = sum(p.confidence for p in pages) / len(pages) if pages else 0.0

    logger.info(
        "mistral_ocr_complete",
        total_pages=len(pages),
        elapsed_ms=elapsed_ms,
        avg_confidence=round(avg_conf, 3),
    )

    return OcrDocumentResult(
        pages=pages,
        total_pages=len(pages),
        method="mistral_ocr",
        overall_confidence=avg_conf,
        processing_time_ms=elapsed_ms,
    )


def ocr_page_batch(
    pdf_bytes: bytes,
    page_indices: list[int],
    dpi: int,
    max_workers: int,
) -> list[OcrPageResult]:
    """OCR a specific batch of PDF pages (0-based indices) via Mistral.

    The Mistral API accepts a `pages` parameter with 0-based page numbers.
    """
    b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
    document = {
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{b64}",
    }

    try:
        response = _ocr_process(document, pages=page_indices)
    except Exception as exc:
        logger.error("mistral_ocr_page_batch_failed", error=str(exc))
        return [
            OcrPageResult(page=idx + 1, text="", tables=[], confidence=0.0, has_embedded_text=False)
            for idx in page_indices
        ]

    results: list[OcrPageResult] = []
    response_pages = list(response.pages) if response.pages else []

    for j, idx in enumerate(page_indices):
        if j < len(response_pages):
            pg = response_pages[j]
            text = pg.markdown.strip() if hasattr(pg, "markdown") and pg.markdown else ""
        else:
            text = ""
        results.append(OcrPageResult(
            page=idx + 1,
            text=text,
            tables=[],
            confidence=0.90 if text else 0.0,
            has_embedded_text=False,
        ))

    return results
