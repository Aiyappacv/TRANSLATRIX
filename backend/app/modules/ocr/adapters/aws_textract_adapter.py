"""
AWS Textract Adapter
OCR using Amazon Textract
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

from .base import BaseOCRProvider, OCRResult, OCRPageResult, TextBlock, OCRError

logger = structlog.get_logger(__name__)


class AWSTextractProvider(BaseOCRProvider):
    """
    AWS Textract provider
    Enterprise-grade OCR with form and table extraction
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.region = config.get("region", "us-east-1") if config else "us-east-1"
        self.aws_access_key = config.get("aws_access_key") if config else None
        self.aws_secret_key = config.get("aws_secret_key") if config else None

    def recognize_image(
        self, image_path: Path, language: str = "en"
    ) -> OCRPageResult:
        """
        Perform OCR on a single image using AWS Textract

        Args:
            image_path: Path to image file
            language: Language code

        Returns:
            OCRPageResult with recognized text
        """
        try:
            import boto3

            logger.info("aws_textract_recognize_image", image_path=str(image_path))

            # Initialize Textract client
            if self.aws_access_key and self.aws_secret_key:
                textract = boto3.client(
                    "textract",
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                )
            else:
                textract = boto3.client("textract", region_name=self.region)

            # Read image
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # Call Textract
            response = textract.detect_document_text(Document={"Bytes": image_bytes})

            # Extract text blocks
            text_blocks = []
            text_parts = []
            confidences = []

            for block in response["Blocks"]:
                if block["BlockType"] == "LINE":
                    text = block.get("Text", "")
                    confidence = block.get("Confidence", 0.0) / 100.0  # Convert to 0-1
                    bbox = block["Geometry"]["BoundingBox"]

                    # Convert normalized bbox to absolute coordinates (assume 1000x1000)
                    bbox_abs = [
                        bbox["Left"] * 1000,
                        bbox["Top"] * 1000,
                        (bbox["Left"] + bbox["Width"]) * 1000,
                        (bbox["Top"] + bbox["Height"]) * 1000,
                    ]

                    text_blocks.append(
                        TextBlock(text=text, confidence=confidence, bbox=bbox_abs)
                    )
                    text_parts.append(text)
                    confidences.append(confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRPageResult(
                page_number=1,
                text=full_text,
                confidence=avg_confidence,
                text_blocks=text_blocks,
            )

        except ImportError:
            raise OCRError("boto3 library not installed. Install with: pip install boto3")
        except Exception as e:
            logger.error("aws_textract_error", error=str(e))
            raise OCRError(f"AWS Textract recognition failed: {str(e)}")

    def recognize_pdf(
        self, pdf_path: Path, language: str = "en"
    ) -> OCRResult:
        """
        Perform OCR on a PDF document using AWS Textract

        Args:
            pdf_path: Path to PDF file
            language: Language code

        Returns:
            OCRResult with recognized text from all pages
        """
        try:
            import boto3
            import time

            logger.info("aws_textract_recognize_pdf", pdf_path=str(pdf_path))

            # For PDFs, Textract requires async processing via S3
            # This is a simplified version that processes as images
            # For production, implement S3 bucket upload and async job processing

            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            pages = []
            all_confidences = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = f"/tmp/textract_page_{page_num}.png"
                pix.save(img_path)

                # Process page
                page_result = self.recognize_image(Path(img_path), language)
                page_result.page_number = page_num + 1
                page_result.width = pix.width
                page_result.height = pix.height

                pages.append(page_result)
                all_confidences.append(page_result.confidence)

                # Cleanup
                Path(img_path).unlink(missing_ok=True)

                # Rate limiting
                time.sleep(0.1)

            doc.close()

            full_text = "\n\n".join(page.text for page in pages)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            return OCRResult(
                pages=pages,
                full_text=full_text,
                average_confidence=avg_confidence,
                metadata={"provider": "aws_textract", "language": language},
            )

        except ImportError as e:
            raise OCRError(f"Required library not installed: {str(e)}")
        except Exception as e:
            logger.error("aws_textract_pdf_error", error=str(e))
            raise OCRError(f"AWS Textract PDF recognition failed: {str(e)}")

    def get_supported_languages(self) -> List[str]:
        """AWS Textract supports many languages"""
        return [
            "en", "es", "it", "pt", "fr", "de", "nl",
        ]
