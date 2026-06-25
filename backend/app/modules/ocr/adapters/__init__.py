"""OCR adapter registry and factory helpers."""

from functools import lru_cache
from typing import Dict

import structlog

from app.config import settings

from .base import BaseOCRProvider, OCRError
from .mistral_adapter import MistralOCRProvider
from .paddleocr_adapter import PaddleOCRProvider
from .azure_di_adapter import AzureDocumentIntelligenceProvider
from .aws_textract_adapter import AWSTextractProvider

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def _provider_registry() -> Dict[str, BaseOCRProvider]:
    """Lazily build the available OCR provider instances."""

    mistral_provider = MistralOCRProvider({
        "api_key": settings.MISTRAL_API_KEY,
        "model": settings.MISTRAL_OCR_MODEL,
    })

    registry: Dict[str, BaseOCRProvider] = {
        "mistral": mistral_provider,
        "mistral_ocr": mistral_provider,
        "paddleocr": PaddleOCRProvider({"languages": settings.PADDLEOCR_LANG}),
        "azure_di": AzureDocumentIntelligenceProvider({
            "endpoint": settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            "api_key": settings.AZURE_DOCUMENT_INTELLIGENCE_KEY,
        }),
        "aws_textract": AWSTextractProvider({
            "region": settings.AWS_TEXTRACT_REGION,
            "aws_access_key": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_key": settings.AWS_SECRET_ACCESS_KEY,
        }),
    }

    return registry


def get_ocr_adapter(provider_name: str) -> BaseOCRProvider:
    """Return the configured OCR provider instance for the supplied name."""

    registry = _provider_registry()
    key = (provider_name or "").strip().lower()

    if not key:
        raise OCRError("OCR provider name must be provided")

    provider = registry.get(key)
    if provider is None:
        logger.error("unknown_ocr_provider", provider=provider_name)
        raise OCRError(f"OCR provider '{provider_name}' is not supported")

    return provider


__all__ = ["get_ocr_adapter", "BaseOCRProvider", "OCRError"]
