from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Callable

logger = logging.getLogger("translatrix.preview.renderer")

PAGE_RENDERER: str | None = None


def _render_pypdfium2(path: Path, page: int, dpi: int) -> tuple[bytes, int]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        page_count = len(pdf)
        if page < 1 or page > page_count:
            raise IndexError(f"Page {page} out of range (1-{page_count})")
        scale = dpi / 72.0
        bitmap = pdf[page - 1].render(scale=scale)
        pil_image = bitmap.to_pil()
        buf = BytesIO()
        pil_image.save(buf, format="PNG")
        return buf.getvalue(), page_count
    finally:
        pdf.close()


def _render_pymupdf(path: Path, page: int, dpi: int) -> tuple[bytes, int]:
    import fitz

    doc = fitz.open(str(path))
    try:
        page_count = doc.page_count
        if page < 1 or page > page_count:
            raise IndexError(f"Page {page} out of range (1-{page_count})")
        pix = doc[page - 1].get_pixmap(dpi=dpi)
        return pix.tobytes("png"), page_count
    finally:
        doc.close()


def _render_pdf2image(path: Path, page: int, dpi: int) -> tuple[bytes, int]:
    from pdf2image import convert_from_path

    images = convert_from_path(str(path), dpi=dpi, first_page=page, last_page=page)
    if not images:
        raise RuntimeError(f"pdf2image returned no image for page {page}")
    buf = BytesIO()
    images[0].save(buf, format="PNG")

    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    return buf.getvalue(), page_count


_RENDERERS: list[tuple[str, str, Callable[..., tuple[bytes, int]]]] = [
    ("pypdfium2", "pypdfium2", _render_pypdfium2),
    ("PyMuPDF (fitz)", "fitz", _render_pymupdf),
    ("pdf2image", "pdf2image", _render_pdf2image),
]

_available: str | None = None
_render_fn: Callable[..., tuple[bytes, int]] | None = None


def init_renderer() -> str | None:
    global _available, _render_fn, PAGE_RENDERER

    for name, mod_name, fn in _RENDERERS:
        try:
            __import__(mod_name)
            logger.info("PDF renderer: %s — available", name)
            _available = name
            _render_fn = fn
            PAGE_RENDERER = name
            return name
        except ImportError:
            logger.warning("PDF renderer: %s — not available", name)
            continue

    logger.error("PDF renderer: NO renderer available — preview service degraded")
    _available = None
    _render_fn = None
    PAGE_RENDERER = None
    return None


def render_page(path: Path, page: int, dpi: int = 150) -> tuple[bytes, int]:
    if _render_fn is None:
        raise RuntimeError("No PDF renderer is available")
    return _render_fn(path, page, dpi)


def available_renderer() -> str | None:
    return _available
