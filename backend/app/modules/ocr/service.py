"""
OCR Service
Orchestrates OCR processing using various providers
"""
from typing import Optional, Dict, Any
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime
import structlog
import time
import tempfile
import os

from app.config import settings
from app.modules.ocr.models import OCRResult, OCRPage, OCRProvider, OCRStatus
from app.modules.ocr.adapters.base import BaseOCRProvider, OCRError
from app.modules.ocr.adapters.paddleocr_adapter import PaddleOCRProvider
from app.modules.ocr.adapters.azure_di_adapter import AzureDocumentIntelligenceProvider
from app.modules.ocr.adapters.aws_textract_adapter import AWSTextractProvider
from app.modules.ocr.adapters.mistral_adapter import MistralOCRProvider
from app.modules.files.models import IngestedFile

logger = structlog.get_logger(__name__)


class OCRService:
    """
    OCR orchestration service
    Manages OCR provider selection and processing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Register OCR providers
        mistral_config = {
            "api_key": settings.MISTRAL_API_KEY,
            "model": settings.MISTRAL_OCR_MODEL,
        }
        mistral_config.update(self.config.get("mistral", {}))

        paddle_config = self.config.get("paddleocr", {})
        azure_config = self.config.get("azure_di", {
            "endpoint": settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            "api_key": settings.AZURE_DOCUMENT_INTELLIGENCE_KEY,
        })
        aws_config = self.config.get("aws_textract", {
            "region": settings.AWS_TEXTRACT_REGION,
            "aws_access_key": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_key": settings.AWS_SECRET_ACCESS_KEY,
        })

        mistral_provider = MistralOCRProvider(mistral_config)

        self.providers: Dict[str, BaseOCRProvider] = {
            "mistral": mistral_provider,
            "mistral_ocr": mistral_provider,
            "paddleocr": PaddleOCRProvider(paddle_config),
            "azure_di": AzureDocumentIntelligenceProvider(azure_config),
            "aws_textract": AWSTextractProvider(aws_config),
        }

    def _get_provider(self, provider_name: str) -> BaseOCRProvider:
        """
        Get OCR provider by name

        Args:
            provider_name: Provider identifier

        Returns:
            BaseOCRProvider instance

        Raises:
            ValueError: If provider not found
        """
        provider = self.providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"OCR provider '{provider_name}' not found")
        return provider

    async def process_file(
        self,
        db: Session,
        file_id: UUID,
        tenant_id: UUID,
        file_service,  # FileService instance for downloading from MinIO
        provider: str = "mistral",
        language: str = "en",
        force_reprocess: bool = False,
    ) -> OCRResult:
        """
        Process file with OCR

        Args:
            db: Database session
            file_id: File ID
            tenant_id: Tenant ID
            file_service: FileService instance for downloading from storage
            provider: OCR provider name
            language: Language code
            force_reprocess: Force reprocessing

        Returns:
            OCRResult

        Raises:
            ValueError: If file not found
            OCRError: If OCR processing fails
        """
        # Get file
        file = db.query(IngestedFile).filter(
            IngestedFile.id == file_id,
            IngestedFile.tenant_id == tenant_id,
        ).first()

        if not file:
            raise ValueError(f"File {file_id} not found")

        # Check for existing result
        existing = db.query(OCRResult).filter(
            OCRResult.file_id == file_id
        ).first()

        if existing and not force_reprocess:
            logger.info("ocr_result_exists", file_id=file_id)
            return existing

        # Create or update result record
        if existing:
            result = existing
            result.status = OCRStatus.PROCESSING
            result.updated_at = datetime.utcnow()
        else:
            # Map provider string to enum
            provider_enum = OCRProvider.MISTRAL if provider.lower() in {"mistral", "mistral_ocr"} else OCRProvider.PADDLEOCR
            if provider.lower() == "azure_di":
                provider_enum = OCRProvider.AZURE_DI
            elif provider.lower() == "aws_textract":
                provider_enum = OCRProvider.AWS_TEXTRACT

            result = OCRResult(
                tenant_id=tenant_id,
                file_id=file_id,
                provider=provider_enum,
                language=language,
                status=OCRStatus.PROCESSING,
            )
            db.add(result)

        db.commit()
        db.refresh(result)

        temp_file_path = None
        try:
            start_time = time.time()

            # Download file from MinIO to temporary location
            logger.info("downloading_file_from_storage", file_id=file_id, storage_path=file.storage_path)
            file_content = await file_service.download_file(file_id, tenant_id)

            if not file_content:
                raise OCRError(f"Failed to download file from storage: {file.storage_path}")

            # Create temporary file with appropriate extension
            file_extension = Path(file.original_filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_content)
                temp_file_path = Path(temp_file.name)

            logger.info("file_downloaded_to_temp", temp_path=str(temp_file_path), size=len(file_content))

            # Get OCR provider
            ocr_provider = self._get_provider(provider)

            logger.info(
                "starting_ocr",
                file_id=file_id,
                provider=provider,
                language=language,
            )

            # Perform OCR based on file type
            if file.mime_type == "application/pdf":
                ocr_result = ocr_provider.recognize_pdf(temp_file_path, language)
            else:
                # Treat as image
                page_result = ocr_provider.recognize_image(temp_file_path, language)
                # Convert to full OCR result
                from app.modules.ocr.adapters.base import OCRResult as AdapterOCRResult
                ocr_result = AdapterOCRResult(
                    pages=[page_result],
                    full_text=page_result.text,
                    average_confidence=page_result.confidence,
                    metadata={"provider": provider, "language": language},
                )

            # Update result
            result.total_pages = len(ocr_result.pages)
            result.average_confidence = ocr_result.average_confidence
            result.full_text = ocr_result.full_text
            result.provider_metadata = ocr_result.metadata
            result.status = OCRStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.processing_time_seconds = time.time() - start_time

            db.commit()

            # Save page-level results
            for page_data in ocr_result.pages:
                ocr_page = OCRPage(
                    ocr_result_id=result.id,
                    page_number=page_data.page_number,
                    text=page_data.text,
                    confidence=page_data.confidence,
                    text_blocks=[
                        {
                            "text": block.text,
                            "confidence": block.confidence,
                            "bbox": block.bbox,
                        }
                        for block in page_data.text_blocks
                    ],
                    width=page_data.width,
                    height=page_data.height,
                )
                db.add(ocr_page)

            db.commit()
            db.refresh(result)

            logger.info(
                "ocr_complete",
                file_id=file_id,
                pages=result.total_pages,
                avg_confidence=result.average_confidence,
            )

            return result

        except Exception as e:
            logger.error("ocr_error", file_id=file_id, error=str(e))
            result.status = OCRStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            db.commit()
            raise OCRError(f"OCR processing failed: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_file_path and temp_file_path.exists():
                try:
                    os.unlink(temp_file_path)
                    logger.info("temp_file_cleaned_up", temp_path=str(temp_file_path))
                except Exception as e:
                    logger.warning("temp_file_cleanup_failed", temp_path=str(temp_file_path), error=str(e))

    def get_ocr_result(
        self, db: Session, file_id: UUID, tenant_id: UUID
    ) -> Optional[OCRResult]:
        """
        Get OCR result for file

        Args:
            db: Database session
            file_id: File ID
            tenant_id: Tenant ID

        Returns:
            OCRResult or None
        """
        return db.query(OCRResult).filter(
            OCRResult.file_id == file_id,
            OCRResult.tenant_id == tenant_id,
        ).first()

    def get_ocr_pages(
        self, db: Session, ocr_result_id: UUID
    ) -> list[OCRPage]:
        """
        Get OCR pages for result

        Args:
            db: Database session
            ocr_result_id: OCR result ID

        Returns:
            List of OCRPage
        """
        return db.query(OCRPage).filter(
            OCRPage.ocr_result_id == ocr_result_id
        ).order_by(OCRPage.page_number).all()
