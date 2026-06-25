"""
PDF Parser Adapter
Extract text and tables from PDF files using PyPDF2 and pdfplumber
"""
from pathlib import Path
from typing import List, Dict, Any
import structlog

from .base import BaseExtractor, ExtractionResult, ExtractionError

logger = structlog.get_logger(__name__)


class PDFExtractor(BaseExtractor):
    """
    PDF content extractor using PyPDF2 and pdfplumber
    Attempts native text extraction before falling back to OCR
    """

    def __init__(self):
        self.supported_mimes = [
            "application/pdf",
        ]

    def can_extract(self, file_path: Path, mime_type: str) -> bool:
        """Check if this is a PDF file"""
        return mime_type in self.supported_mimes or file_path.suffix.lower() == ".pdf"

    def extract(
        self,
        file_path: Path,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract content from PDF file

        Args:
            file_path: Path to PDF file
            extract_tables: Whether to extract tables
            extract_metadata: Whether to extract metadata

        Returns:
            ExtractionResult with extracted content
        """
        try:
            import PyPDF2
            import pdfplumber

            logger.info("extracting_pdf", file_path=str(file_path))

            # Extract text using PyPDF2 (fast)
            text_parts = []
            metadata = {}
            page_count = 0

            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                page_count = len(pdf_reader.pages)

                # Extract metadata
                if extract_metadata and pdf_reader.metadata:
                    metadata = {
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "subject": pdf_reader.metadata.get("/Subject", ""),
                        "creator": pdf_reader.metadata.get("/Creator", ""),
                        "producer": pdf_reader.metadata.get("/Producer", ""),
                        "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                    }

                # Extract text from all pages
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)

            # Extract tables using pdfplumber (more advanced)
            tables = []
            if extract_tables:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        for page_num, page in enumerate(pdf.pages, 1):
                            page_tables = page.extract_tables()
                            if page_tables:
                                for table_idx, table_data in enumerate(page_tables):
                                    if table_data and len(table_data) > 0:
                                        # First row as headers
                                        headers = table_data[0] if table_data[0] else []
                                        rows = table_data[1:] if len(table_data) > 1 else []

                                        tables.append({
                                            "page": page_num,
                                            "table_index": table_idx,
                                            "headers": headers,
                                            "rows": rows,
                                        })
                except Exception as e:
                    logger.warning("table_extraction_failed", error=str(e))

            # Calculate confidence based on text extraction success
            confidence = 0.95 if full_text.strip() else 0.0

            logger.info(
                "pdf_extraction_complete",
                pages=page_count,
                text_length=len(full_text),
                tables=len(tables),
                confidence=confidence,
            )

            return ExtractionResult(
                text=full_text,
                tables=tables,
                metadata=metadata,
                page_count=page_count,
                confidence=confidence,
            )

        except ImportError as e:
            raise ExtractionError(f"Required PDF library not installed: {str(e)}")
        except Exception as e:
            logger.error("pdf_extraction_error", error=str(e), file_path=str(file_path))
            raise ExtractionError(f"Failed to extract PDF content: {str(e)}")

    def get_supported_formats(self) -> List[str]:
        """Return supported MIME types"""
        return self.supported_mimes
