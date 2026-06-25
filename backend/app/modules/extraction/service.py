"""
Extraction Service
Orchestrates content extraction from various file formats
Uses Gemini 2.5 Pro as the primary extraction engine for AI-powered extraction.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime
import structlog
import time
import tempfile

from app.config import settings
from app.modules.extraction.models import FileExtractionResult, ExtractionMethod, ExtractionStatus
from app.modules.extraction.adapters.base import BaseExtractor, ExtractionError
from app.modules.extraction.adapters.pdf_parser import PDFExtractor
from app.modules.extraction.adapters.docx_parser import DOCXExtractor
from app.modules.extraction.adapters.spreadsheet_parser import SpreadsheetExtractor
from app.modules.extraction.adapters.gemini_extractor import GeminiExtractor
from app.modules.extraction.adapters.mistral_fallback import MistralFallbackExtractor
from app.modules.ingestion.data_intake_service import DataIntakeService
from app.modules.files.models import IngestedFile
from app.modules.storage.adapters.base import BaseStorage
from app.modules.storage.service import get_storage_adapter

logger = structlog.get_logger(__name__)


class ExtractionService:
    """
    Content extraction orchestration service
    Routes files to appropriate extractors based on MIME type.
    Gemini 2.5 Pro is the primary extraction engine for AI-powered extraction
    including OCR understanding, layout analysis, table extraction, and entity extraction.
    """

    def __init__(self):
        # Instantiate Gemini extractor only if API key is configured.
        if getattr(settings, "GEMINI_API_KEY", None):
            gemini_config = {
                "api_key": settings.GEMINI_API_KEY,
                "model": settings.GEMINI_EXTRACTION_MODEL,
            }
            try:
                self.gemini_extractor = GeminiExtractor(gemini_config)
            except Exception:
                # Fail-safe: if Gemini can't be instantiated, fall back silently
                # and rely on Mistral/native extractors instead of crashing.
                logger.warning("gemini_instantiation_failed")
                self.gemini_extractor = None
        else:
            logger.info("gemini_api_key_missing", message="GEMINI_API_KEY not set, Gemini extractor disabled; using fallback extractors")
            self.gemini_extractor = None

        # Mistral fallback extractor (used when Gemini is not available or fails)
        self.mistral_fallback = MistralFallbackExtractor()
        self.extractors: list[BaseExtractor] = [
            PDFExtractor(),
            DOCXExtractor(),
            SpreadsheetExtractor(),
        ]

    def _get_extractor_candidates(self, file_path: Path, mime_type: str) -> List[BaseExtractor]:
        """Return extractors that can handle the supplied file in priority order.

        Strategy: prefer Gemini when available, then a Mistral fallback that
        uses deterministic heuristics, then the native file-parsers (PDF/DOCX/etc.).
        """
        candidates: List[BaseExtractor] = []

        # If Gemini extractor is available and configured, prefer it first.
        if getattr(self, 'gemini_extractor', None) is not None:
            try:
                gemini_available = self.gemini_extractor.can_extract(file_path, mime_type)
            except Exception:
                gemini_available = False

            if gemini_available:
                candidates.append(self.gemini_extractor)
                # After Gemini failure, try the Mistral-based deterministic fallback
                if self.mistral_fallback.can_extract(file_path, mime_type):
                    candidates.append(self.mistral_fallback)
        else:
            # Gemini not configured or failed to instantiate — prefer Mistral fallback first
            logger.info("gemini_unavailable_using_mistral", mime_type=mime_type)
            if self.mistral_fallback.can_extract(file_path, mime_type):
                candidates.append(self.mistral_fallback)

        for extractor in self.extractors:
            if extractor.can_extract(file_path, mime_type):
                candidates.append(extractor)

        if not candidates:
            logger.warning("no_extractor_found", mime_type=mime_type)

        return candidates

    def _get_extractor(self, file_path: Path, mime_type: str) -> Optional[BaseExtractor]:
        candidates = self._get_extractor_candidates(file_path, mime_type)
        if candidates:
            primary = candidates[0]
            log_data = {
                "extractor": primary.__class__.__name__,
                "mime_type": mime_type,
            }
            if isinstance(primary, GeminiExtractor):
                log_data["model"] = settings.GEMINI_EXTRACTION_MODEL
            logger.info("extractor_found", **log_data)
            return primary
        return None

    async def extract_file(
        self,
        db: Session,
        file_id: UUID,
        tenant_id: UUID,
        use_ocr: bool = False,
        extract_tables: bool = True,
        extract_metadata: bool = True,
        force_reprocess: bool = False,
    ) -> FileExtractionResult:
        """
        Extract content from file using Gemini 2.5 Pro as the primary extraction engine.

        Args:
            db: Database session
            file_id: File ID
            tenant_id: Tenant ID
            use_ocr: Force OCR extraction
            extract_tables: Extract tables
            extract_metadata: Extract metadata
            force_reprocess: Force reprocessing

        Returns:
            FileExtractionResult

        Raises:
            ValueError: If file not found
            ExtractionError: If extraction fails
        """
        # Get file
        file = db.query(IngestedFile).filter(
            IngestedFile.id == file_id,
            IngestedFile.tenant_id == tenant_id,
        ).first()

        if not file:
            raise ValueError(f"File {file_id} not found")

        # Check for existing result
        existing = db.query(FileExtractionResult).filter(
            FileExtractionResult.file_id == file_id
        ).first()

        if existing and not force_reprocess:
            logger.info("extraction_result_exists", file_id=file_id)
            return existing

        # Create or update result record
        if existing:
            result = existing
            result.status = ExtractionStatus.PROCESSING
            result.updated_at = datetime.utcnow()
        else:
            result = FileExtractionResult(
                tenant_id=tenant_id,
                file_id=file_id,
                method=ExtractionMethod.OCR if use_ocr else ExtractionMethod.NATIVE_TEXT,
                use_ocr=use_ocr,
                status=ExtractionStatus.PROCESSING,
            )
            db.add(result)

        db.commit()
        db.refresh(result)

        file_path: Optional[Path] = None
        try:
            start_time = time.time()

            # Download file from storage
            storage = await get_storage_adapter()
            content_bytes = b""
            if file.storage_path:
                try:
                    content_bytes = await storage.download_file(file.storage_path)
                except Exception as download_err:
                    logger.error(
                        "file_download_failed",
                        file_id=file_id,
                        storage_path=file.storage_path,
                        error=str(download_err),
                    )

            if not content_bytes:
                raise ExtractionError(f"File content not available at {file.storage_path}")

            # Write to temporary file
            suffix = ""
            if file.file_type:
                suffix = f".{file.file_type.strip('.')}"
            elif file.original_filename:
                suffix = Path(file.original_filename).suffix

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".bin") as tmp:
                tmp.write(content_bytes)
                file_path = Path(tmp.name)

            try:
                # If OCR is forced, use OCR service (to be implemented)
                if use_ocr:
                    logger.info("ocr_extraction_required", file_id=file_id)
                    # TODO: Integrate with OCR service
                    raise ExtractionError("OCR extraction not yet implemented in this method")

                # Get appropriate extractor(s) in priority order
                extractor_candidates = self._get_extractor_candidates(file_path, file.mime_type)

                if not extractor_candidates:
                    raise ExtractionError(f"No extractor available for MIME type: {file.mime_type}")

                extraction_result = None
                selected_extractor: Optional[BaseExtractor] = None
                last_error: Optional[ExtractionError] = None

                # Classify document type prior to extraction so type-aware
                # extraction guidance can be applied.
                storage = await get_storage_adapter()
                data_intake = DataIntakeService(db, storage)
                try:
                    classification = await data_intake._classify_document(content_bytes, file.original_filename or f"file_{file_id}", file.mime_type or "application/octet-stream")
                    detected_type = classification.get("label") if classification else None
                except Exception:
                    detected_type = None

                for extractor in extractor_candidates:
                    logger.info("starting_extraction", file_id=file_id, extractor=extractor.__class__.__name__)
                    try:
                       # Pass document_type when supported
                       kwargs = {"extract_tables": extract_tables, "extract_metadata": extract_metadata}
                       if hasattr(extractor, 'extract'):
                           # If extractor accepts document_type, pass it
                           try:
                               extraction_result = extractor.extract(file_path, **kwargs, document_type=detected_type)
                           except TypeError:
                               extraction_result = extractor.extract(file_path, **kwargs)
                       else:
                           extraction_result = extractor.extract(file_path, **kwargs)

                       selected_extractor = extractor
                       break
                    except ExtractionError as extractor_error:
                       last_error = extractor_error
                       logger.warning(
                           "extraction_attempt_failed",
                           file_id=file_id,
                           extractor=extractor.__class__.__name__,
                           error=str(extractor_error),
                       )

                if not selected_extractor or not extraction_result:
                    error_message = (
                        str(last_error)
                        if last_error
                        else f"No extractor available for MIME type: {file.mime_type}"
                    )
                    raise ExtractionError(error_message)

                # Update result
                result.extracted_text = extraction_result.text
                result.extracted_tables = extraction_result.tables
                # Ensure metadata contains consistent keys across extractors
                metadata = dict(extraction_result.metadata or {})
                # Normalize model/provider metadata
                provider = metadata.get("provider") or (selected_extractor.__class__.__name__.lower())
                model = metadata.get("model") or getattr(selected_extractor, 'model', None) or settings.GEMINI_EXTRACTION_MODEL
                metadata["extraction_model_used"] = provider if provider else selected_extractor.__class__.__name__
                metadata["extraction_model_name"] = model
                # extraction_time_ms may be provided by extractor metadata
                if "extraction_time_ms" not in metadata:
                    metadata["extraction_time_ms"] = int((time.time() - start_time) * 1000)

                result.extracted_metadata = metadata
                result.confidence_score = extraction_result.confidence
                result.page_count = extraction_result.page_count
                result.word_count = extraction_result.word_count
                result.has_tables = extraction_result.has_tables
                result.has_images = False  # TODO: Detect images
                result.status = ExtractionStatus.COMPLETED
                result.completed_at = datetime.utcnow()
                result.processing_time_seconds = time.time() - start_time

                # Determine method used
                if isinstance(selected_extractor, GeminiExtractor):
                    result.method = ExtractionMethod.OCR if use_ocr else ExtractionMethod.HYBRID
                    result.parser_version = f"gemini-2.5-pro-{settings.GEMINI_EXTRACTION_MODEL}"
                elif isinstance(selected_extractor, PDFExtractor):
                    result.method = ExtractionMethod.NATIVE_TEXT
                    result.parser_version = None
                elif isinstance(selected_extractor, SpreadsheetExtractor):
                    result.method = ExtractionMethod.SPREADSHEET
                    result.parser_version = None
                else:
                    result.method = ExtractionMethod.NATIVE_TEXT
                    result.parser_version = None

                db.commit()
                db.refresh(result)

                logger.info(
                    "extraction_complete",
                    file_id=file_id,
                    text_length=len(extraction_result.text),
                    tables=len(extraction_result.tables),
                    confidence=extraction_result.confidence,
                    extractor=selected_extractor.__class__.__name__,
                )

                return result

            except Exception as e:
                logger.error("extraction_error", file_id=file_id, error=str(e))
                result.status = ExtractionStatus.FAILED
                result.error_message = str(e)
                result.completed_at = datetime.utcnow()
                db.commit()
                raise ExtractionError(f"Extraction failed: {str(e)}")

        finally:
            # Clean up temporary file
            if file_path and file_path.exists():
                file_path.unlink(missing_ok=True)

    def get_extraction_result(
        self, db: Session, file_id: UUID, tenant_id: UUID
    ) -> Optional[FileExtractionResult]:
        """
        Get extraction result for file

        Args:
            db: Database session
            file_id: File ID
            tenant_id: Tenant ID

        Returns:
            FileExtractionResult or None
        """
        return db.query(FileExtractionResult).filter(
            FileExtractionResult.file_id == file_id,
            FileExtractionResult.tenant_id == tenant_id,
        ).first()
