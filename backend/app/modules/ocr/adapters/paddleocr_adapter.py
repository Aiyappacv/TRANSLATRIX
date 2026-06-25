"""
PaddleOCR Adapter
OCR using PaddleOCR library (open-source, multi-language)
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

from .base import BaseOCRProvider, OCRResult, OCRPageResult, TextBlock, OCRError

logger = structlog.get_logger(__name__)


class PaddleOCRProvider(BaseOCRProvider):
    """
    PaddleOCR provider
    Free, open-source OCR with excellent multi-language support
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._ocr_engine = None
        self.supported_languages = [
            "en", "ch", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "ar", "hi"
        ]

    def _get_ocr_engine(self, language: str = "en"):
        """
        Lazy load OCR engine

        Args:
            language: Language code

        Returns:
            PaddleOCR instance
        """
        try:
            from paddleocr import PaddleOCR

            # Map common language codes to PaddleOCR language codes
            lang_map = {
                "en": "en",
                "zh": "ch",
                "fr": "french",
                "de": "german",
                "es": "spanish",
                "it": "italian",
                "pt": "portuguese",
                "ru": "russian",
                "ja": "japan",
                "ko": "korean",
                "ar": "arabic",
                "hi": "hindi",
            }

            paddle_lang = lang_map.get(language, "en")

            # Initialize PaddleOCR with configuration
            ocr = PaddleOCR(
                use_angle_cls=True,  # Enable text angle classification
                lang=paddle_lang,
            )

            return ocr

        except ImportError:
            raise OCRError("PaddleOCR library not installed. Install with: pip install paddleocr")
        except Exception as e:
            raise OCRError(f"Failed to initialize PaddleOCR: {str(e)}")

    def recognize_image(
        self, image_path: Path, language: str = "en"
    ) -> OCRPageResult:
        """
        Perform OCR on a single image

        Args:
            image_path: Path to image file
            language: Language code

        Returns:
            OCRPageResult with recognized text
        """
        try:
            logger.info("paddleocr_recognize_image", image_path=str(image_path), language=language)

            ocr = self._get_ocr_engine(language)
            result = ocr.predict(str(image_path))

            if not result or not result[0]:
                logger.warning("no_text_detected", image_path=str(image_path))
                return OCRPageResult(
                    page_number=1,
                    text="",
                    confidence=0.0,
                    text_blocks=[],
                )

            # Process OCR results
            text_blocks = []
            text_parts = []
            confidences = []

            for line in result[0]:
                # PaddleOCR format: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)]
                bbox_points = line[0]
                text_info = line[1]
                text = text_info[0]
                confidence = text_info[1]

                # Convert bbox points to [x1, y1, x2, y2]
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]
                bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

                text_blocks.append(
                    TextBlock(text=text, confidence=confidence, bbox=bbox)
                )
                text_parts.append(text)
                confidences.append(confidence)

            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            logger.info(
                "paddleocr_complete",
                text_blocks=len(text_blocks),
                avg_confidence=avg_confidence,
            )

            return OCRPageResult(
                page_number=1,
                text=full_text,
                confidence=avg_confidence,
                text_blocks=text_blocks,
            )

        except Exception as e:
            logger.error("paddleocr_error", error=str(e), image_path=str(image_path))
            raise OCRError(f"PaddleOCR recognition failed: {str(e)}")

    def recognize_pdf(
        self, pdf_path: Path, language: str = "en"
    ) -> OCRResult:
        """
        Perform OCR on a PDF document

        Args:
            pdf_path: Path to PDF file
            language: Language code

        Returns:
            OCRResult with recognized text from all pages
        """
        try:
            import fitz  # PyMuPDF

            logger.info("paddleocr_recognize_pdf", pdf_path=str(pdf_path), language=language)

            # Convert PDF pages to images and process
            doc = fitz.open(pdf_path)
            pages = []
            all_confidences = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Render page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                img_path = f"/tmp/page_{page_num}.png"
                pix.save(img_path)

                # Perform OCR on image
                page_result = self.recognize_image(Path(img_path), language)
                page_result.page_number = page_num + 1
                page_result.width = pix.width
                page_result.height = pix.height

                pages.append(page_result)
                all_confidences.append(page_result.confidence)

                # Cleanup temp image
                Path(img_path).unlink(missing_ok=True)

            doc.close()

            # Combine results
            full_text = "\n\n".join(page.text for page in pages)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            logger.info(
                "paddleocr_pdf_complete",
                pages=len(pages),
                avg_confidence=avg_confidence,
            )

            return OCRResult(
                pages=pages,
                full_text=full_text,
                average_confidence=avg_confidence,
                metadata={"provider": "paddleocr", "language": language},
            )

        except ImportError:
            raise OCRError("PyMuPDF library not installed. Install with: pip install pymupdf")
        except Exception as e:
            logger.error("paddleocr_pdf_error", error=str(e), pdf_path=str(pdf_path))
            raise OCRError(f"PaddleOCR PDF recognition failed: {str(e)}")

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return self.supported_languages
