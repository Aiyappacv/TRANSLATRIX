"""
Azure Document Intelligence Adapter
OCR using Azure's Document Intelligence (formerly Form Recognizer)
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

from .base import BaseOCRProvider, OCRResult, OCRPageResult, TextBlock, OCRError

logger = structlog.get_logger(__name__)


class AzureDocumentIntelligenceProvider(BaseOCRProvider):
    """
    Azure Document Intelligence provider
    Enterprise-grade OCR with form and table recognition
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.endpoint = config.get("endpoint") if config else None
        self.api_key = config.get("api_key") if config else None

    def recognize_image(
        self, image_path: Path, language: str = "en"
    ) -> OCRPageResult:
        """
        Perform OCR on a single image using Azure DI

        Args:
            image_path: Path to image file
            language: Language code

        Returns:
            OCRPageResult with recognized text
        """
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            if not self.endpoint or not self.api_key:
                raise OCRError("Azure Document Intelligence credentials not configured")

            logger.info("azure_di_recognize_image", image_path=str(image_path))

            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )

            with open(image_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-read", document=f)
                result = poller.result()

            # Extract text blocks
            text_blocks = []
            text_parts = []
            confidences = []

            for page in result.pages:
                for line in page.lines:
                    bbox = [
                        line.polygon[0].x,
                        line.polygon[0].y,
                        line.polygon[2].x,
                        line.polygon[2].y,
                    ]

                    text_blocks.append(
                        TextBlock(
                            text=line.content,
                            confidence=line.confidence if hasattr(line, "confidence") else 1.0,
                            bbox=bbox,
                        )
                    )
                    text_parts.append(line.content)
                    if hasattr(line, "confidence"):
                        confidences.append(line.confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.95

            return OCRPageResult(
                page_number=1,
                text=full_text,
                confidence=avg_confidence,
                text_blocks=text_blocks,
            )

        except ImportError:
            raise OCRError("Azure Form Recognizer SDK not installed. Install with: pip install azure-ai-formrecognizer")
        except Exception as e:
            logger.error("azure_di_error", error=str(e))
            raise OCRError(f"Azure DI recognition failed: {str(e)}")

    def recognize_pdf(
        self, pdf_path: Path, language: str = "en"
    ) -> OCRResult:
        """
        Perform OCR on a PDF document using Azure DI

        Args:
            pdf_path: Path to PDF file
            language: Language code

        Returns:
            OCRResult with recognized text from all pages
        """
        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            if not self.endpoint or not self.api_key:
                raise OCRError("Azure Document Intelligence credentials not configured")

            logger.info("azure_di_recognize_pdf", pdf_path=str(pdf_path))

            client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )

            with open(pdf_path, "rb") as f:
                poller = client.begin_analyze_document("prebuilt-read", document=f)
                result = poller.result()

            # Process pages
            pages = []
            all_confidences = []

            for page_num, page in enumerate(result.pages, 1):
                text_blocks = []
                text_parts = []
                confidences = []

                for line in page.lines:
                    bbox = [
                        line.polygon[0].x,
                        line.polygon[0].y,
                        line.polygon[2].x,
                        line.polygon[2].y,
                    ]

                    conf = line.confidence if hasattr(line, "confidence") else 1.0
                    text_blocks.append(
                        TextBlock(text=line.content, confidence=conf, bbox=bbox)
                    )
                    text_parts.append(line.content)
                    confidences.append(conf)

                page_text = "\n".join(text_parts)
                page_confidence = sum(confidences) / len(confidences) if confidences else 0.95

                pages.append(
                    OCRPageResult(
                        page_number=page_num,
                        text=page_text,
                        confidence=page_confidence,
                        text_blocks=text_blocks,
                        width=int(page.width) if hasattr(page, "width") else None,
                        height=int(page.height) if hasattr(page, "height") else None,
                    )
                )
                all_confidences.append(page_confidence)

            full_text = "\n\n".join(page.text for page in pages)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.95

            return OCRResult(
                pages=pages,
                full_text=full_text,
                average_confidence=avg_confidence,
                metadata={"provider": "azure_di", "language": language},
            )

        except ImportError:
            raise OCRError("Azure Form Recognizer SDK not installed")
        except Exception as e:
            logger.error("azure_di_pdf_error", error=str(e))
            raise OCRError(f"Azure DI PDF recognition failed: {str(e)}")

    def get_supported_languages(self) -> List[str]:
        """Azure DI supports 100+ languages"""
        return [
            "en", "zh", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "ar", "hi",
            "nl", "sv", "pl", "tr", "cs", "da", "fi", "no", "hu", "ro", "th", "vi",
        ]
