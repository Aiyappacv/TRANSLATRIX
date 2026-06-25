"""
Mistral OCR Adapter
Integrates with Mistral's hosted OCR API for high-fidelity document extraction.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

from app.config import settings

from .base import BaseOCRProvider, OCRResult, OCRPageResult, TextBlock, OCRError

logger = structlog.get_logger(__name__)


class MistralOCRProvider(BaseOCRProvider):
    """OCR provider that uses Mistral's managed OCR API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = (self.config.get("api_key") or settings.MISTRAL_API_KEY or "").strip()
        self.model = (self.config.get("model") or settings.MISTRAL_OCR_MODEL or "mistral-ocr-latest").strip()
        self.timeout = float(self.config.get("timeout", 180.0))

        if not self.api_key:
            logger.warning("mistral_ocr_api_key_missing", message="Mistral OCR will fail without MISTRAL_API_KEY")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def recognize_image(self, image_path: Path, language: str = "en") -> OCRPageResult:  # noqa: ARG002 - interface parity
        logger.info("mistral_ocr_recognize_image", path=str(image_path))
        response = self._perform_request(image_path.read_bytes(), mime_type=self._guess_mime(image_path, default="image/png"), kind="image")
        pages = self._build_page_results(response)
        if not pages:
            raise OCRError("Mistral OCR returned no content for image")
        page = pages[0]
        return page

    def recognize_pdf(self, pdf_path: Path, language: str = "en") -> OCRResult:  # noqa: ARG002 - interface parity
        logger.info("mistral_ocr_recognize_pdf", path=str(pdf_path))
        response = self._perform_request(pdf_path.read_bytes(), mime_type="application/pdf", kind="document")
        pages = self._build_page_results(response)
        if not pages:
            raise OCRError("Mistral OCR returned no pages for PDF")

        average_confidence = sum(page.confidence for page in pages) / len(pages)
        full_text = "\n\n".join(page.text for page in pages)

        return OCRResult(
            pages=pages,
            full_text=full_text,
            average_confidence=average_confidence,
            metadata={"provider": "mistral_ocr", "model": self.model},
        )

    def get_supported_languages(self) -> List[str]:
        # Mistral OCR auto-detects multiple languages internally.
        return ["auto"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _perform_request(self, content: bytes, *, mime_type: str, kind: str) -> Dict[str, Any]:
        if not self.api_key:
            raise OCRError("MISTRAL_API_KEY is not configured")

        encoded = base64.b64encode(content).decode("ascii")
        document_payload: Dict[str, Any]
        if kind == "image":
            document_payload = {"type": "image_url", "image_url": f"data:{mime_type};base64,{encoded}"}
        else:
            document_payload = {"type": "document_url", "document_url": f"data:{mime_type};base64,{encoded}"}

        try:
            response = httpx.post(
                "https://api.mistral.ai/v1/ocr",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "document": document_payload,
                    "confidence_scores_granularity": "page",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise OCRError("Unexpected response format from Mistral OCR")
            return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "mistral_ocr_http_error",
                status_code=exc.response.status_code,
                response_text=exc.response.text,
            )
            raise OCRError(f"Mistral OCR request failed: {exc.response.text}") from exc
        except httpx.HTTPError as exc:
            logger.error("mistral_ocr_request_failed", error=str(exc))
            raise OCRError(f"Failed to call Mistral OCR: {exc}") from exc

    def _build_page_results(self, response: Dict[str, Any]) -> List[OCRPageResult]:
        pages_payload = response.get("pages") or []
        page_results: List[OCRPageResult] = []

        for index, page in enumerate(pages_payload, start=1):
            text = page.get("markdown") or page.get("text") or ""
            confidence_scores = page.get("confidence_scores") or {}
            confidence = confidence_scores.get("average_page_confidence_score") or 0.0
            page_number = page.get("page_number") or index

            text_block = TextBlock(
                text=text,
                confidence=confidence,
                bbox=[0.0, 0.0, 0.0, 0.0],
                metadata={"provider": "mistral_ocr"},
            )

            page_results.append(
                OCRPageResult(
                    page_number=page_number,
                    text=text,
                    confidence=confidence,
                    text_blocks=[text_block],
                    width=None,
                    height=None,
                )
            )

        return page_results

    @staticmethod
    def _guess_mime(path: Path, default: str) -> str:
        import mimetypes

        mime = mimetypes.guess_type(str(path))[0]
        return mime or default
