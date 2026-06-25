"""
Extraction Worker
Extract content from documents using Gemini 2.5 Pro as the primary extraction engine.
Supports OCR understanding, layout analysis, table extraction, and entity extraction.
Multi-page PDFs are split into concurrent chunks and merged for speed and reliability.
"""
from typing import Dict, Any
from pathlib import Path
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor, as_completed
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.config import settings
from app.modules.files.models import IngestedFile, FileStatus
from app.modules.extraction.models import FileExtractionResult, ExtractionMethod, ExtractionStatus
from app.modules.extraction.adapters.gemini_extractor import GeminiExtractor
from app.modules.extraction.adapters.mistral_fallback import MistralFallbackExtractor
from app.modules.extraction.adapters.base import ExtractionResult
from app.modules.extraction.adapters.pdf_parser import PDFExtractor
from app.modules.extraction.adapters.docx_parser import DOCXExtractor
from app.modules.extraction.adapters.spreadsheet_parser import SpreadsheetExtractor
from datetime import datetime
import structlog
import uuid
import time

logger = structlog.get_logger(__name__)


class ExtractionTask(Task):
    """Base task with error handling"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("extraction_task_failed", task_id=task_id, error=str(exc))


def _build_metadata_from_merged(merged: Any, model: str) -> dict:
    return {
        "document_type": merged.document_type,
        "language": merged.language,
        "extracted_fields": merged.extracted_fields,
        "field_confidence": merged.field_confidence,
        "field_pages": merged.field_pages,
        "model": model,
        "provider": "gemini",
        "failed_chunks": merged.failed_chunks,
    }


@celery_app.task(
    name="extraction.extract",
    bind=True,
    base=ExtractionTask,
    max_retries=3,
    autoretry_for=(OSError, ConnectionError, TimeoutError),
    retry_backoff=True,
    time_limit=600,
)
def extract_file(self, file_id: str) -> Dict[str, Any]:
    """
    Extract content from document files using Gemini 2.5 Pro.
    Multi-page PDFs are split into concurrent chunks and merged.
    Queued and executed asynchronously. One failed document does not impact others.
    """
    db = SessionLocal()
    start_time = time.time()
    try:
        logger.info("extracting_file_via_gemini_pro", file_id=file_id)

        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        file.status = FileStatus.EXTRACTING
        db.commit()

        gemini_extractor = None
        mistral_fallback = MistralFallbackExtractor()

        if getattr(settings, "GEMINI_API_KEY", None):
            gemini_config = {
                "api_key": settings.GEMINI_API_KEY,
                "model": settings.GEMINI_EXTRACTION_MODEL,
                "classify_model": settings.EXTRACTION_CLASSIFY_MODEL,
            }
            try:
                gemini_extractor = GeminiExtractor(gemini_config)
            except Exception as e:
                logger.warning("gemini_instantiation_failed_in_worker", error=str(e))
                gemini_extractor = None

        # Download file content from storage using storage adapter
        from app.modules.storage.service import get_storage_adapter
        import asyncio
        storage = asyncio.run(get_storage_adapter())
        content = asyncio.run(storage.download_file(file.storage_path))

        file_path = Path(file.storage_path)
        mime_type = file.mime_type

        # Prefer Gemini if configured and can handle this file; otherwise use fallback
        if gemini_extractor is not None and gemini_extractor.can_extract(file_path, mime_type):
            extraction_method = ExtractionMethod.HYBRID
            is_pdf = file.file_type.lower() == "pdf"

            if is_pdf:
                from app.modules.extraction.chunking import plan_chunks, extract_chunk_pdf_bytes, ChunkingError
                from app.modules.extraction.merge_engine import merge_chunk_results, ChunkExtractionResult
                try:
                    total_pages, page_ranges = plan_chunks(content, settings.EXTRACTION_CHUNK_SIZE)
                except ChunkingError as exc:
                    raise RuntimeError(f"Failed to analyze PDF structure: {exc}") from exc

                if len(page_ranges) == 1:
                    extraction_result = gemini_extractor.extract(file_path)
                else:
                    logger.info(
                        "extraction_chunked_start",
                        file_id=file_id, total_pages=total_pages,
                        total_chunks=len(page_ranges),
                        chunk_size=settings.EXTRACTION_CHUNK_SIZE,
                    )

                    first_range = page_ranges[0]
                    first_pdf_chunk = extract_chunk_pdf_bytes(content, first_range, len(page_ranges))
                    document_type = gemini_extractor.classify_document(first_pdf_chunk.pdf_bytes)

                    chunk_results: list[ChunkExtractionResult] = []
                    with ThreadPoolExecutor(max_workers=settings.MAX_EXTRACTION_WORKERS) as executor:
                        futures = {}

                        def _submit(pr, pdf_bytes):
                            future = executor.submit(
                                gemini_extractor.extract_chunk,
                                pdf_bytes,
                                document_type=document_type,
                                start_page=pr.start_page,
                                end_page=pr.end_page,
                                chunk_index=pr.chunk_index,
                                total_chunks=len(page_ranges),
                                total_pages=total_pages,
                            )
                            futures[future] = pr

                        _submit(first_range, first_pdf_chunk.pdf_bytes)

                        for pr in page_ranges[1:]:
                            pdf_chunk = extract_chunk_pdf_bytes(content, pr, len(page_ranges))
                            _submit(pr, pdf_chunk.pdf_bytes)

                        for future in as_completed(futures):
                            pr = futures[future]
                            try:
                                result = future.result()
                                chunk_results.append(result)
                            except Exception as exc:
                                logger.error(
                                    "extraction_chunk_failed_in_worker",
                                    file_id=file_id, chunk_index=pr.chunk_index,
                                    pages=f"{pr.start_page}-{pr.end_page}", error=str(exc),
                                )
                                chunk_results.append(ChunkExtractionResult(
                                    chunk_index=pr.chunk_index,
                                    start_page=pr.start_page,
                                    end_page=pr.end_page,
                                    total_chunks=len(page_ranges),
                                    success=False,
                                    error=str(exc),
                                    retries=settings.EXTRACTION_MAX_RETRIES,
                                ))

                    merged = merge_chunk_results(chunk_results, total_pages)

                    if merged.chunks_succeeded == 0:
                        raise RuntimeError(
                            f"All {total_chunks} extraction chunks failed for "
                            f"this {total_pages}-page document."
                        )

                    extraction_result = ExtractionResult(
                        text=merged.full_text,
                        tables=merged.tables,
                        metadata=_build_metadata_from_merged(merged, settings.GEMINI_EXTRACTION_MODEL),
                        page_count=merged.page_count,
                        word_count=merged.word_count,
                        confidence=merged.overall_confidence,
                    )

                    logger.info(
                        "extraction_chunked_complete",
                        file_id=file_id, total_pages=total_pages,
                        chunks_succeeded=merged.chunks_succeeded,
                        chunks_failed=len(merged.failed_chunks),
                        confidence=merged.overall_confidence,
                    )
            else:
                extraction_result = gemini_extractor.extract(file_path)
        else:
            # Use Mistral fallback if available for robust OCR/deterministic parsing
            if mistral_fallback.can_extract(file_path, mime_type):
                extraction_result = mistral_fallback.extract(file_path)
                extraction_method = ExtractionMethod.HYBRID if getattr(extraction_result, 'metadata', {}).get('provider') == 'mistral' else ExtractionMethod.NATIVE_TEXT
            else:
                extractor = _get_fallback_extractor(file.file_type)
                extraction_result = extractor.extract(file_path)
                extraction_method = ExtractionMethod.NATIVE_TEXT

        processing_time = time.time() - start_time

        result = FileExtractionResult(
            tenant_id=file.tenant_id,
            file_id=file.id,
            method=extraction_method,
            use_ocr=False,
            status=ExtractionStatus.COMPLETED,
            extracted_text=extraction_result.text,
            extracted_tables=extraction_result.tables,
            extracted_metadata=extraction_result.metadata,
            confidence_score=extraction_result.confidence,
            page_count=extraction_result.page_count,
            word_count=extraction_result.word_count,
            has_tables=extraction_result.has_tables,
            has_images=False,
            processing_time_seconds=round(processing_time, 2),
            parser_version=f"gemini-2.5-pro-{settings.GEMINI_EXTRACTION_MODEL}" if extraction_method == ExtractionMethod.HYBRID else "native",
            completed_at=datetime.utcnow(),
        )
        db.add(result)

        file.status = FileStatus.EXTRACTED
        db.commit()

        if file.file_type.lower() in ['png', 'jpg', 'jpeg', 'tiff', 'pdf']:
            from app.workers.ocr_worker import process_file_ocr
            process_file_ocr.delay(str(file.id))

        logger.info(
            "extraction_completed_via_gemini_pro",
            file_id=file_id, processing_time_seconds=processing_time,
        )
        return {"file_id": file_id, "status": "extracted"}

    except Exception as e:
        logger.error("extraction_failed", file_id=file_id, error=str(e))
        if db:
            file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
            if file:
                file.status = FileStatus.FAILED
                db.commit()
        raise
    finally:
        db.close()


@celery_app.task(
    name="extraction.spreadsheet",
    bind=True,
    base=ExtractionTask,
    max_retries=2
)
def extract_spreadsheet(self, file_id: str) -> Dict[str, Any]:
    """
    Extract data from Excel/CSV files using Gemini 2.5 Pro for structured extraction.
    """
    db = SessionLocal()
    start_time = time.time()
    try:
        logger.info("extracting_spreadsheet_via_gemini_pro", file_id=file_id)

        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        gemini_extractor = None
        mistral_fallback = MistralFallbackExtractor()
        if getattr(settings, "GEMINI_API_KEY", None):
            gemini_config = {
                "api_key": settings.GEMINI_API_KEY,
                "model": settings.GEMINI_EXTRACTION_MODEL,
            }
            try:
                gemini_extractor = GeminiExtractor(gemini_config)
            except Exception as e:
                logger.warning("gemini_instantiation_failed_in_worker_spreadsheet", error=str(e))
                gemini_extractor = None

        file_path = Path(file.storage_path)
        if gemini_extractor is not None and gemini_extractor.can_extract(file_path, file.mime_type):
            extraction_result = gemini_extractor.extract(file_path)
        else:
            # fallback to Mistral or native spreadsheet extractor
            if mistral_fallback.can_extract(file_path, file.mime_type):
                extraction_result = mistral_fallback.extract(file_path)
            else:
                extraction_result = SpreadsheetExtractor().extract(file_path)

        processing_time = time.time() - start_time

        result = FileExtractionResult(
            tenant_id=file.tenant_id,
            file_id=file.id,
            method=ExtractionMethod.SPREADSHEET,
            use_ocr=False,
            status=ExtractionStatus.COMPLETED,
            extracted_text=extraction_result.text,
            extracted_tables=extraction_result.tables,
            extracted_metadata=extraction_result.metadata,
            confidence_score=extraction_result.confidence,
            page_count=extraction_result.page_count,
            word_count=extraction_result.word_count,
            has_tables=extraction_result.has_tables,
            has_images=False,
            processing_time_seconds=round(processing_time, 2),
            parser_version=f"gemini-2.5-pro-{settings.GEMINI_EXTRACTION_MODEL}",
            completed_at=datetime.utcnow(),
        )
        db.add(result)

        db.commit()

        logger.info(
            "spreadsheet_extraction_completed_via_gemini_pro",
            file_id=file_id, processing_time_seconds=processing_time,
        )
        return {"file_id": file_id, "status": "extracted"}

    finally:
        db.close()


def _get_fallback_extractor(file_type: str):
    """Fallback parser selection for types Gemini cannot handle.
    Note: python-docx only supports .docx, not legacy .doc format."""
    parsers = {
        "pdf": PDFExtractor(),
        "docx": DOCXExtractor(),
        "xlsx": SpreadsheetExtractor(),
        "xls": SpreadsheetExtractor(),
        "csv": SpreadsheetExtractor(),
    }
    return parsers.get(file_type.lower(), PDFExtractor())
