"""
Base OCR Provider Interface
Abstract base class for OCR providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TextBlock:
    """Single text block with bounding box and confidence"""
    text: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OCRPageResult:
    """OCR result for a single page"""
    page_number: int
    text: str
    confidence: float
    text_blocks: List[TextBlock]
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class OCRResult:
    """Complete OCR result for a document"""
    pages: List[OCRPageResult]
    full_text: str
    average_confidence: float
    metadata: Optional[Dict[str, Any]] = None

    @property
    def total_pages(self) -> int:
        return len(self.pages)


class BaseOCRProvider(ABC):
    """
    Base class for OCR providers
    Implements the Strategy pattern for different OCR services
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OCR provider

        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def recognize_image(
        self, image_path: Path, language: str = "en"
    ) -> OCRPageResult:
        """
        Perform OCR on a single image

        Args:
            image_path: Path to image file
            language: Language code (ISO 639-1)

        Returns:
            OCRPageResult with recognized text

        Raises:
            OCRError: If OCR fails
        """
        pass

    @abstractmethod
    def recognize_pdf(
        self, pdf_path: Path, language: str = "en"
    ) -> OCRResult:
        """
        Perform OCR on a PDF document

        Args:
            pdf_path: Path to PDF file
            language: Language code (ISO 639-1)

        Returns:
            OCRResult with recognized text from all pages

        Raises:
            OCRError: If OCR fails
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes

        Returns:
            List of ISO 639-1 language codes
        """
        pass

    def get_provider_name(self) -> str:
        """
        Get provider name

        Returns:
            Provider identifier
        """
        return self.__class__.__name__.replace("Provider", "").lower()


class OCRError(Exception):
    """Raised when OCR operation fails"""
    pass
