"""
PDF chunking utilities for the multi-page extraction pipeline.

Large PDFs are never sent to Gemini as a single request — they are split
into independent page-range chunks (PdfChunk) which are uploaded and
extracted separately, then merged. This keeps every Gemini request small
and bounded regardless of total document size (1 page or 1000+ pages),
and ensures we only ever hold one chunk's rendered bytes in memory at a
time per worker rather than the whole document.
"""
from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF
import structlog

logger = structlog.get_logger(__name__)


class ChunkingError(Exception):
    pass


@dataclass(frozen=True)
class PageRange:
    chunk_index: int
    start_page: int  # 1-based, inclusive
    end_page: int  # 1-based, inclusive


@dataclass
class PdfChunk:
    chunk_index: int
    start_page: int  # 1-based, inclusive
    end_page: int  # 1-based, inclusive
    total_chunks: int
    pdf_bytes: bytes


def count_pdf_pages(content: bytes) -> int:
    """Independently verify page count via PyMuPDF rather than trusting a
    model's self-reported page_count, which is what previously let a
    truncated single-shot Gemini response masquerade as a 1-page document."""
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            return doc.page_count
    except Exception as exc:
        raise ChunkingError(f"Failed to read PDF for page counting: {exc}") from exc


def compute_page_ranges(total_pages: int, chunk_size: int) -> list[PageRange]:
    """Pure planning step — no PDF bytes touched here, just arithmetic, so
    this can be logged and inspected before any extraction work starts."""
    if total_pages <= 0:
        raise ChunkingError("Document has no pages")
    chunk_size = max(1, chunk_size)

    ranges: list[PageRange] = []
    start = 1
    index = 0
    while start <= total_pages:
        end = min(start + chunk_size - 1, total_pages)
        ranges.append(PageRange(chunk_index=index, start_page=start, end_page=end))
        start = end + 1
        index += 1
    return ranges


def extract_chunk_pdf_bytes(content: bytes, page_range: PageRange, total_chunks: int) -> PdfChunk:
    """Render a single page-range chunk as its own standalone PDF document.

    Only this chunk's bytes are materialised — the source document is opened,
    the relevant pages are copied into a fresh in-memory PDF, and the source
    handle is closed immediately, so processing a 1000-page document never
    requires holding more than one chunk's worth of rendered bytes at once."""
    try:
        with fitz.open(stream=content, filetype="pdf") as src:
            chunk_doc = fitz.open()
            try:
                chunk_doc.insert_pdf(src, from_page=page_range.start_page - 1, to_page=page_range.end_page - 1)
                chunk_bytes = chunk_doc.tobytes(garbage=3, deflate=True)
            finally:
                chunk_doc.close()
    except Exception as exc:
        raise ChunkingError(
            f"Failed to split pages {page_range.start_page}-{page_range.end_page}: {exc}"
        ) from exc

    return PdfChunk(
        chunk_index=page_range.chunk_index,
        start_page=page_range.start_page,
        end_page=page_range.end_page,
        total_chunks=total_chunks,
        pdf_bytes=chunk_bytes,
    )


def plan_chunks(content: bytes, chunk_size: int) -> tuple[int, list[PageRange]]:
    """Returns (total_pages, page_ranges) without rendering any chunk bytes."""
    total_pages = count_pdf_pages(content)
    ranges = compute_page_ranges(total_pages, chunk_size)
    logger.info(
        "extraction_chunk_plan",
        total_pages=total_pages,
        total_chunks=len(ranges),
        chunk_size=chunk_size,
        ranges=[f"{r.start_page}-{r.end_page}" for r in ranges],
    )
    return total_pages, ranges
