"""
Base Extractor Interface
Abstract base class for content extraction adapters
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


class ExtractionResult:
    """Extraction result container"""
    def __init__(
        self,
        text: str,
        tables: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        page_count: Optional[int] = None,
        word_count: Optional[int] = None,
        confidence: float = 1.0,
    ):
        self.text = text
        self.tables = tables or []
        self.metadata = metadata or {}
        self.page_count = page_count
        self.word_count = word_count or len(text.split())
        self.confidence = confidence
        self.has_tables = len(self.tables) > 0


class BaseExtractor(ABC):
    """
    Base class for content extraction adapters
    Implements the Strategy pattern for different file formats
    """

    @abstractmethod
    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        """
        Check if this extractor can handle the given file

        Args:
            file_path: Path to the file
            mime_type: MIME type of the file

        Returns:
            True if this extractor can handle the file
        """
        pass

    @abstractmethod
    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract content from the file

        Args:
            file_path: Path to the file
            extract_tables: Whether to extract tables
            extract_metadata: Whether to extract metadata
            **kwargs: Additional extractor-specific options

        Returns:
            ExtractionResult containing extracted content

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported MIME types

        Returns:
            List of supported MIME types
        """
        return []


class ExtractionError(Exception):
    """Raised when content extraction fails"""
    pass
