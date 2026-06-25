from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import os
import structlog
import tempfile
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.config import settings
from app.modules.files.models import IngestedFile, FileStatus, IngestionBatch, BatchStatus
from app.modules.ingestion.data_intake_models import (
    IntakeRegistry,
    IntakeEvent,
    IntakeStatus,
    SourceChannel,
)
from app.modules.ingestion.data_intake_schemas import (
    IntakeRegistryEntry,
    IntakeRegistryListResponse,
    DuplicateMatch,
    CheckDuplicateResponse,
    PreviewResponse,
    PreviewPage,
    ExtractNavigationResponse,
    DeleteResponse,
    IntakeEventResponse,
)
from app.modules.ingestion.tiered_storage import (
    TieredStorageManager,
    LakeTier,
    ProcessingStep,
    DocumentEmbedding,
)
from app.modules.storage.adapters.base import BaseStorage

logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".xml", ".json"}
MAX_FILE_SIZE_BYTES = settings.max_file_size_bytes
SEMANTIC_SIMILARITY_THRESHOLD = 0.92

# Maps Gemini's ISO 639-1 language codes onto the capitalized English names the
# rest of the pipeline expects (processing_validation_issues() compares against
# names like "English", not codes) — an unrecognised code safely falls back to "Unknown".
_GEMINI_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "nl": "Dutch", "ar": "Arabic", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
    "ml": "Malayalam", "bn": "Bengali", "ru": "Russian", "tr": "Turkish", "vi": "Vietnamese", "th": "Thai",
}

_embedding_model = None
_embedding_model_load_failed = False


def _get_embedding_model():
    """Lazily load the sentence-transformers model once per process and reuse it.

    Re-instantiating SentenceTransformer on every call (the previous behavior)
    added several seconds of model-load overhead to every single upload.
    """
    global _embedding_model, _embedding_model_load_failed
    if _embedding_model is not None:
        return _embedding_model
    if _embedding_model_load_failed:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedding_model
    except ImportError:
        logger.warning("sentence_transformers not available for semantic dedup")
        _embedding_model_load_failed = True
        return None


class DataIntakeService:
    def __init__(self, db: Session, storage: BaseStorage):
        self.db = db
        self.storage = storage
        self.tiered = TieredStorageManager(db, storage)

    def _log_event(
        self,
        registry_id: UUID,
        event_type: str,
        status: str,
        message: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> IntakeEvent:
        event = IntakeEvent(
            registry_id=registry_id,
            event_type=event_type,
            status=status,
            message=message,
            metadata_json=metadata_json,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def _update_status(self, registry: IntakeRegistry, status: IntakeStatus) -> None:
        registry.status = status
        registry.updated_at = datetime.utcnow()
        if status in (IntakeStatus.METADATA_READY, IntakeStatus.READY_FOR_EXTRACTION):
            registry.processed_at = datetime.utcnow()
        self.db.commit()

    def _to_entry(self, registry: IntakeRegistry) -> IntakeRegistryEntry:
        # Normalize status to lowercase for API consumers to preserve
        # backward-compatible presentation irrespective of DB enum labels.
        status_value = registry.status.value.lower() if hasattr(registry.status, "value") else str(registry.status).lower()
        return IntakeRegistryEntry(
            id=str(registry.id),
            file_id=str(registry.file_id) if registry.file_id else None,
            original_filename=registry.original_filename,
            source_channel=registry.source_channel.value if hasattr(registry.source_channel, "value") else str(registry.source_channel),
            document_type=registry.document_type,
            language=registry.language,
            status=status_value,
            tier=registry.tier,
            is_duplicate=registry.is_duplicate,
            duplicate_of_id=str(registry.duplicate_of_id) if registry.duplicate_of_id else None,
            duplicate_similarity=registry.duplicate_similarity,
            checksum=registry.checksum,
            file_size=registry.file_size,
            mime_type=registry.mime_type,
            page_count=registry.page_count,
            language_detected=registry.language_detected,
            orientation=registry.orientation,
            processing_metadata=registry.processing_metadata,
            created_at=registry.created_at,
            processed_at=registry.processed_at,
        )

    # ── Hash-based Exact Duplicate Detection ─────────────────────

    def _compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _check_exact_duplicate(
        self, checksum: str, tenant_id: UUID, exclude_id: Optional[UUID] = None
    ) -> Optional[IntakeRegistry]:
        query = self.db.query(IntakeRegistry).filter(
            IntakeRegistry.checksum == checksum,
            IntakeRegistry.tenant_id == tenant_id,
            IntakeRegistry.status != IntakeStatus.FAILED,
        )
        if exclude_id is not None:
            query = query.filter(IntakeRegistry.id != exclude_id)
        return query.order_by(IntakeRegistry.created_at.asc()).first()

    # ── Semantic Duplicate Detection (all-MiniLM-L6-v2 + FAISS nearest-neighbor search) ──

    def _compute_embedding(self, text: str) -> list[float]:
        try:
            model = _get_embedding_model()
            if model is None:
                return []
            embedding = model.encode(text[:10000], normalize_embeddings=True)
            return embedding.tolist()
        except Exception as exc:
            logger.error("embedding_failed", error=str(exc))
            return []

    async def _check_semantic_duplicate(
        self, content: bytes, tenant_id: UUID, checksum: str
    ) -> Tuple[list[dict[str, Any]], float, Optional[list[float]]]:
        text = content.decode("utf-8", errors="replace")[:10000]
        embedding = self._compute_embedding(text)
        if not embedding:
            return [], 0.0, None

        existing_embeddings = (
            self.db.query(DocumentEmbedding)
            .filter(
                DocumentEmbedding.tenant_id == tenant_id,
                DocumentEmbedding.embedding_dim == 384,
            )
            .all()
        )
        if not existing_embeddings:
            return [], 0.0, embedding

        vectors: list[list[float]] = []
        records: list[DocumentEmbedding] = []
        for existing in existing_embeddings:
            try:
                embedding_bytes = await self.storage.download_file(existing.embedding_path)
                vectors.append(json.loads(embedding_bytes.decode("utf-8")))
                records.append(existing)
            except Exception:
                continue

        if not vectors:
            return [], 0.0, embedding

        import faiss
        import numpy as np

        matrix = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(matrix)
        query = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(query)

        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        k = min(5, len(records))
        similarities, neighbor_indices = index.search(query, k)

        matches: list[dict[str, Any]] = []
        max_similarity = 0.0

        for similarity, idx in zip(similarities[0], neighbor_indices[0]):
            if idx < 0:
                continue
            similarity = float(similarity)
            max_similarity = max(max_similarity, similarity)
            if similarity > 0.75:
                existing = records[idx]
                existing_registry = (
                    self.db.query(IntakeRegistry)
                    .filter(IntakeRegistry.file_id == existing.file_id)
                    .first()
                )
                matches.append({
                    "file_id": str(existing.file_id),
                    "registry_id": str(existing_registry.id) if existing_registry else None,
                    "filename": existing_registry.original_filename if existing_registry else "Unknown",
                    "similarity": round(similarity, 4),
                    "method": "semantic",
                    "uploaded_at": existing_registry.created_at if existing_registry else None,
                })

        matches.sort(key=lambda m: m["similarity"], reverse=True)
        return matches[:5], max_similarity, embedding

    async def _store_embedding(
        self, embedding: list[float], file_id: UUID, tenant_id: UUID, checksum: str
    ) -> None:
        embedding_path = f"embeddings/tenants/{tenant_id}/{file_id}.json"
        try:
            await self.storage.upload_file(
                file_content=json.dumps(embedding).encode("utf-8"),
                object_key=embedding_path,
                content_type="application/json",
                metadata={"tenant_id": str(tenant_id), "file_id": str(file_id), "model": "all-MiniLM-L6-v2"},
            )
        except Exception as exc:
            logger.warning("embedding_store_failed", error=str(exc))
            return

        embed_record = DocumentEmbedding(
            file_id=file_id,
            tenant_id=tenant_id,
            embedding_dim=384,
            embedding_path=embedding_path,
            model_name="all-MiniLM-L6-v2",
            checksum=hashlib.sha256(json.dumps(embedding).encode()).hexdigest(),
        )
        self.db.add(embed_record)
        self.db.commit()

    # ── Preprocessing ────────────────────────────────────────────

    def _preprocess(
        self, content: bytes, filename: str, content_type: Optional[str]
    ) -> dict[str, Any]:
        ext = Path(filename).suffix.lower()
        mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        result: dict[str, Any] = {
            "mime_type": mime,
            "page_count": 0,
            "language_hint": None,
            "orientation": "portrait",
            "has_text": False,
            "word_count": 0,
        }

        if ext == ".pdf":
            if content.startswith(b"%PDF"):
                result["page_count"] = self._count_pdf_pages(content)
                raw_text = self._extract_pdf_text(content)
                if raw_text:
                    result["has_text"] = True
                    result["word_count"] = len(raw_text.split())
                    result["language_hint"] = self._detect_language(raw_text)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif"):
            result["page_count"] = 1
            try:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(content))
                w, h = img.size
                result["orientation"] = "landscape" if w > h else "portrait"
                if ext in (".tiff", ".tif") and hasattr(img, "n_frames"):
                    result["page_count"] = img.n_frames
            except Exception:
                pass
        elif ext in (".xml", ".json"):
            result["page_count"] = 1
            raw_text = content.decode("utf-8", errors="replace")
            if raw_text:
                result["has_text"] = True
                result["word_count"] = len(raw_text.split())
                result["language_hint"] = self._detect_language(raw_text)

        return result

    def _count_pdf_pages(self, content: bytes) -> int:
        try:
            import fitz
            with fitz.open(stream=content, filetype="pdf") as doc:
                return doc.page_count
        except Exception:
            return 0

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            import fitz
            with fitz.open(stream=content, filetype="pdf") as doc:
                return "\n".join(page.get_text() or "" for page in doc)
        except Exception:
            return ""

    def _extract_text_for_classification(self, content: bytes, filename: str, mime_type: str) -> str:
        """Extract a compact text sample (up to 3000 chars) for document classification.

        For PDFs reads the first two pages via PyMuPDF so we never spin up
        the full OCR pipeline just to classify. Returns an empty string when
        no meaningful text can be extracted (scanned PDFs, images) so the
        caller knows to fall back to Gemini vision."""
        ext = Path(filename).suffix.lower()
        try:
            if mime_type == "application/pdf" or ext == ".pdf":
                import fitz
                with fitz.open(stream=content, filetype="pdf") as doc:
                    pages = [doc[i].get_text() or "" for i in range(min(2, len(doc)))]
                text = "\n\n".join(pages).strip()
                # If text is too sparse it's a scanned PDF — return empty so
                # the caller falls back to vision-based classification.
                if len(text) < 30:
                    return ""
                return text[:3000]
            if ext in (".txt", ".csv"):
                return content.decode("utf-8", errors="replace")[:3000]
            if ext in (".xml", ".json"):
                return content.decode("utf-8", errors="replace")[:3000]
        except Exception:
            pass
        return ""

    def _render_first_page_image(self, content: bytes, filename: str, mime_type: str) -> tuple[bytes, str] | None:
        """Return (image_bytes, image_mime) for the first page of the document.

        For PDFs renders page-1 as a JPEG via PyMuPDF; for images returns the
        raw content directly. Returns None when rendering is not possible."""
        ext = Path(filename).suffix.lower()
        try:
            if ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif"):
                effective_mime = mime_type or mimetypes.guess_type(filename)[0] or "image/jpeg"
                return content, effective_mime
            if ext == ".pdf":
                import fitz
                with fitz.open(stream=content, filetype="pdf") as doc:
                    if len(doc) == 0:
                        return None
                    page = doc[0]
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("jpeg")
                    return img_bytes, "image/jpeg"
        except Exception as exc:
            logger.debug("first_page_render_failed", filename=filename, error=str(exc))
        return None

    async def _classify_document(
        self, content: bytes, filename: str, mime_type: str
    ) -> dict[str, Any]:
        """Classify the document as 'invoice' or 'banking_document' using
        deterministic keyword matching on the filename and (when available)
        extracted text. No AI/LLM calls are made — Gemini is reserved for
        field extraction only.

        Returns a dict with label, confidence, reason, and model fields.
        (never returns None; never raises)."""
        text_sample = await asyncio.to_thread(
            self._extract_text_for_classification, content, filename, mime_type
        )

        # ── Rule-based classification ────────────────────────────
        name_lower = filename.lower()
        text_lower = text_sample.lower()

        banking_keywords = {
            "bank", "banking", "statement", "account summary", "swift",
            "wire transfer", "demand draft", "cheque", "check",
            "remittance", "bank confirmation", "credit note", "debit note",
            "financial institution", "account holder", "transaction",
        }
        invoice_keywords = {
            "invoice", "receipt", "purchase order", "bill of lading",
            "packing list", "proforma", "customs", "tax invoice",
            "gst", "vat", "supplier", "vendor", "billing",
        }

        banking_score = sum(1 for kw in banking_keywords if kw in name_lower or kw in text_lower)
        invoice_score = sum(1 for kw in invoice_keywords if kw in name_lower or kw in text_lower)

        if banking_score > invoice_score:
            label = "banking_document"
        else:
            label = "invoice"

        logger.info(
            "document_classified_fallback",
            filename=filename, label=label,
            banking_score=banking_score, invoice_score=invoice_score,
        )
        return {
            "label": label,
            "confidence": 0.6,
            "reason": f"Keyword fallback (banking_score={banking_score}, invoice_score={invoice_score})",
            "model": "rule-based",
            "classified_at": datetime.utcnow().isoformat(),
            "method": "keyword",
        }

    def _detect_language(self, text: str) -> str:
        try:
            from langdetect import DetectorFactory, detect
            DetectorFactory.seed = 0
            lang = detect(text[:10000])
            if lang and len(lang) == 2:
                return lang
        except Exception as exc:
            logger.debug("langdetect_failed", error=str(exc), text_length=len(text))
        sample = text[:3000].lower()
        es_patterns = ["factura", "proveedor", "importe", "cliente", "iva", "nif"]
        if sum(1 for p in es_patterns if p in sample) >= 2:
            return "es"
        fr_patterns = ["facture", "fournisseur", "date", "client", "tva", "numéro"]
        if sum(1 for p in fr_patterns if p in sample) >= 2:
            return "fr"
        de_patterns = ["rechnung", "lieferant", "gesamt", "datum", "kunde", "ust-id"]
        if sum(1 for p in de_patterns if p in sample) >= 2:
            return "de"
        it_patterns = ["fattura", "fornitore", "totale", "data", "cliente", "partita iva"]
        if sum(1 for p in it_patterns if p in sample) >= 2:
            return "it"
        pt_patterns = ["fatura", "fornecedor", "total", "data", "cliente", "nif"]
        if sum(1 for p in pt_patterns if p in sample) >= 2:
            return "pt"
        nl_patterns = ["factuur", "leverancier", "totaal", "datum", "klant", "btw"]
        if sum(1 for p in nl_patterns if p in sample) >= 2:
            return "nl"
        return "en"

    # ── Upload + Full Pipeline ───────────────────────────────────

    # ── Fast Upload: validate + stream + register only ───────────
    #
    # Upload must only perform storage + registration. Everything that needs
    # the full file content (checksum, duplicate detection, page count,
    # language, orientation, embeddings) is deliberately NOT here — it runs
    # in the background metadata pipeline below, so a 500-page PDF or a
    # 500-file batch never makes the HTTP request wait on it.

    def _validate_extension_and_header(self, filename: str, header: bytes) -> Tuple[bool, str]:
        """Cheap, header-only validation for the upload hot path — only needs
        the first chunk of bytes, never the whole file."""
        if not filename:
            return False, "Missing filename"
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        if not header:
            return False, "File is empty"
        if ext == ".pdf" and not header.startswith(b"%PDF"):
            return False, "Corrupted PDF file (missing PDF header)"
        if ext in (".jpg", ".jpeg") and not header.startswith(b"\xff\xd8"):
            return False, "Corrupted JPEG file (missing SOI marker)"
        if ext == ".png" and not header.startswith(b"\x89PNG"):
            return False, "Corrupted PNG file (missing PNG signature)"
        return True, ""

    async def _stream_upload_to_storage(self, upload, tenant_id: UUID, company_id: UUID) -> dict[str, Any]:
        """Validate the header, then stream the upload straight to a local
        temp file in UPLOAD_CHUNK_SIZE_MB chunks — memory use stays flat
        regardless of file size — before handing it to the storage adapter's
        streaming upload. Storage keys are UUID-named and year/month
        partitioned (build_document_key), never the original filename."""
        filename = upload.filename or "unknown"
        ext = Path(filename).suffix.lower()
        chunk_size = settings.upload_chunk_size_bytes
        max_size = settings.max_file_size_bytes

        first_chunk = await upload.read(chunk_size)
        is_valid, error_msg = self._validate_extension_and_header(filename, first_chunk)
        if not is_valid:
            raise ValueError(error_msg)

        document_uuid = uuid.uuid4()
        tmp_dir = Path(tempfile.gettempdir()) / "translatrix_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{document_uuid}{ext}"

        total_size = 0
        try:
            with open(tmp_path, "wb") as fh:
                chunk = first_chunk
                while chunk:
                    total_size += len(chunk)
                    if total_size > max_size:
                        raise ValueError(f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB")
                    fh.write(chunk)
                    chunk = await upload.read(chunk_size)

            if total_size == 0:
                raise ValueError("File is empty")

            mime_guess = upload.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            storage_key = self.storage.build_document_key(str(tenant_id), str(company_id), str(document_uuid), ext)
            await self.storage.upload_stream(tmp_path, storage_key, content_type=mime_guess)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return {
            "document_uuid": document_uuid,
            "filename": filename,
            "file_type": ext.lstrip("."),
            "file_size": total_size,
            "mime_type": mime_guess,
            "storage_path": storage_key,
        }

    async def register_upload(
        self,
        tenant_id: UUID,
        company_id: UUID,
        upload,
        source_channel: SourceChannel = SourceChannel.PORTAL,
    ) -> IntakeRegistryEntry:
        staged = await self._stream_upload_to_storage(upload, tenant_id, company_id)

        batch = IngestionBatch(
            tenant_id=tenant_id, company_id=company_id,
            batch_name=f"Intake {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            status=BatchStatus.COMPLETED, total_files=1, processed_files=1,
        )
        self.db.add(batch)
        self.db.flush()

        ingested = IngestedFile(
            id=staged["document_uuid"], tenant_id=tenant_id, batch_id=batch.id,
            original_filename=staged["filename"], file_type=staged["file_type"],
            file_size=staged["file_size"], mime_type=staged["mime_type"],
            storage_path=staged["storage_path"], status=FileStatus.UPLOADED,
        )
        self.db.add(ingested)

        registry = IntakeRegistry(
            tenant_id=tenant_id, company_id=company_id, file_id=ingested.id,
            original_filename=staged["filename"], source_channel=source_channel,
            status=IntakeStatus.UPLOADED, tier="raw",
            file_size=staged["file_size"], mime_type=staged["mime_type"],
        )
        self.db.add(registry)
        self.db.commit()
        self.db.refresh(registry)

        self._log_event(
            registry.id, "upload", "completed",
            f"File uploaded and registered: {staged['filename']}",
            {"file_id": str(ingested.id), "size": staged["file_size"]},
        )
        return self._to_entry(registry)

    async def register_upload_batch(
        self,
        tenant_id: UUID,
        company_id: UUID,
        uploads: list,
        source_channel: SourceChannel = SourceChannel.PORTAL,
    ) -> Tuple[List[IntakeRegistryEntry], int, int]:
        """Stream every file to storage concurrently (bounded by
        MAX_CONCURRENT_UPLOADS), then create every batch/file/registry row
        in a single transaction — one DB round trip for the whole batch
        instead of one per file. Returns (entries, total, accepted)."""
        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_UPLOADS)

        async def stage_one(upload):
            async with semaphore:
                try:
                    return await self._stream_upload_to_storage(upload, tenant_id, company_id)
                except Exception as exc:
                    logger.error("batch_file_staging_failed", filename=getattr(upload, "filename", "unknown"), error=str(exc), traceback=traceback.format_exc())
                    return None

        staged_results = await asyncio.gather(*(stage_one(u) for u in uploads))
        staged_ok = [s for s in staged_results if s]

        batch = IngestionBatch(
            tenant_id=tenant_id, company_id=company_id,
            batch_name=f"Bulk Intake {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            status=BatchStatus.COMPLETED, total_files=len(uploads),
            processed_files=len(staged_ok), failed_files=len(uploads) - len(staged_ok),
        )
        self.db.add(batch)
        self.db.flush()

        registry_rows: List[IntakeRegistry] = []
        for staged in staged_ok:
            ingested = IngestedFile(
                id=staged["document_uuid"], tenant_id=tenant_id, batch_id=batch.id,
                original_filename=staged["filename"], file_type=staged["file_type"],
                file_size=staged["file_size"], mime_type=staged["mime_type"],
                storage_path=staged["storage_path"], status=FileStatus.UPLOADED,
            )
            registry = IntakeRegistry(
                tenant_id=tenant_id, company_id=company_id, file_id=ingested.id,
                original_filename=staged["filename"], source_channel=source_channel,
                status=IntakeStatus.UPLOADED, tier="raw",
                file_size=staged["file_size"], mime_type=staged["mime_type"],
            )
            self.db.add(ingested)
            self.db.add(registry)
            registry_rows.append(registry)

        self.db.commit()  # single transaction for the entire batch
        for r in registry_rows:
            self.db.refresh(r)

        return [self._to_entry(r) for r in registry_rows], len(uploads), len(staged_ok)

    # ── Background Metadata Pipeline ──────────────────────────────
    # Two independent stages, chained by the job handlers in
    # data_intake_routes.py rather than called directly from here, so the
    # job queue (not this service) owns retry/backoff/failure isolation.

    async def run_metadata_processing(self, registry_id: UUID) -> None:
        """Stage 1: checksum, MIME, page count, language, orientation, and
        cheap exact-checksum duplicate detection. Reaches
        READY_FOR_EXTRACTION on its own — semantic/embedding duplicate
        detection is a separate follow-up stage (run_embedding_detection)
        so a missing optional dependency or slow model inference never
        blocks a document from being usable."""
        registry = self.db.query(IntakeRegistry).filter(IntakeRegistry.id == registry_id).first()
        if not registry or not registry.file_id:
            return
        ingested = self.db.query(IngestedFile).filter(IngestedFile.id == registry.file_id).first()
        if not ingested:
            return

        registry.status = IntakeStatus.METADATA_PROCESSING
        self.db.commit()
        self._log_event(registry.id, "metadata_processing", "processing", "Computing checksum, MIME, page count, language, orientation")

        content = await self.storage.download_file(ingested.storage_path)
        checksum = self._compute_sha256(content)
        preprocessing = await asyncio.to_thread(self._preprocess, content, registry.original_filename, registry.mime_type)

        # Document classification — runs on the same content already in memory.
        # Non-fatal: a classification failure never blocks the upload pipeline.
        classification = await self._classify_document(content, registry.original_filename, preprocessing.get("mime_type") or registry.mime_type or "")
        if classification:
            preprocessing["classification"] = classification

        ingested.checksum = checksum
        ingested.mime_type = preprocessing.get("mime_type", ingested.mime_type)
        registry.checksum = checksum
        registry.mime_type = preprocessing.get("mime_type", registry.mime_type)
        registry.page_count = preprocessing.get("page_count")
        registry.language = preprocessing.get("language_hint")
        registry.language_detected = preprocessing.get("language_hint")
        registry.orientation = preprocessing.get("orientation")
        registry.document_type = classification["label"] if classification else None
        registry.processing_metadata = preprocessing
        registry.status = IntakeStatus.METADATA_READY
        self.db.commit()
        self._log_event(
            registry.id, "metadata_ready", "completed",
            f"Metadata extraction complete. Classification: {classification['label'] if classification else 'unknown'}",
        )

        exact_dup = self._check_exact_duplicate(checksum, registry.tenant_id, exclude_id=registry.id)
        if exact_dup:
            registry.is_duplicate = True
            registry.duplicate_of_id = exact_dup.id
            registry.duplicate_similarity = 1.0
            ingested.is_duplicate = True
            self._log_event(registry.id, "duplicate_detected", "completed", f"Exact duplicate of '{exact_dup.original_filename}'")

        registry.status = IntakeStatus.READY_FOR_EXTRACTION
        registry.processed_at = datetime.utcnow()
        self.db.commit()
        self._log_event(registry.id, "ready_for_extraction", "completed", f"Document ready for extraction: {registry.original_filename}")

    async def run_embedding_detection(self, registry_id: UUID) -> None:
        """Stage 2 (independent, non-blocking): semantic duplicate detection
        via sentence-transformers + FAISS. Runs after the document is
        already READY_FOR_EXTRACTION; failures here (including the optional
        dependency simply not being installed) are logged and otherwise
        ignored — they never change the document's usability."""
        registry = self.db.query(IntakeRegistry).filter(IntakeRegistry.id == registry_id).first()
        if not registry or not registry.file_id or registry.is_duplicate:
            return
        ingested = self.db.query(IngestedFile).filter(IngestedFile.id == registry.file_id).first()
        if not ingested:
            return

        try:
            content = await self.storage.download_file(ingested.storage_path)
            matches, max_similarity, embedding = await self._check_semantic_duplicate(
                content, registry.tenant_id, registry.checksum or ""
            )
        except Exception as exc:
            logger.warning("embedding_detection_failed", registry_id=str(registry_id), error=str(exc))
            return

        if embedding:
            try:
                await self._store_embedding(embedding, ingested.id, registry.tenant_id, registry.checksum or "")
            except Exception as exc:
                logger.warning("embedding_storage_failed", error=str(exc))

        if max_similarity >= SEMANTIC_SIMILARITY_THRESHOLD and matches:
            registry.is_duplicate = True
            registry.duplicate_similarity = max_similarity
            match = matches[0]
            if match.get("registry_id"):
                try:
                    registry.duplicate_of_id = UUID(match["registry_id"])
                except ValueError:
                    pass
            self.db.commit()
            self._log_event(registry.id, "semantic_duplicate_detected", "completed", f"Semantic duplicate detected (similarity={max_similarity:.2f})")

    # ── Check Duplicate (pre-upload) ────────────────────────────

    async def check_duplicate(
        self,
        tenant_id: UUID,
        filename: str,
        content: bytes,
    ) -> CheckDuplicateResponse:
        checksum = self._compute_sha256(content)

        exact_dup = self._check_exact_duplicate(checksum, tenant_id)
        matches: list[dict] = []
        max_similarity = 0.0
        is_exact = False

        if exact_dup:
            is_exact = True
            matches.append({
                "file_id": str(exact_dup.file_id) if exact_dup.file_id else "",
                "registry_id": str(exact_dup.id),
                "filename": exact_dup.original_filename,
                "similarity": 1.0,
                "method": "exact_hash",
                "uploaded_at": exact_dup.created_at,
            })
            max_similarity = 1.0

        if not is_exact:
            semantic_matches, max_similarity, _ = await self._check_semantic_duplicate(
                content, tenant_id, checksum
            )
            matches.extend(semantic_matches)

        return CheckDuplicateResponse(
            is_exact_duplicate=is_exact,
            is_semantic_duplicate=not is_exact and max_similarity >= SEMANTIC_SIMILARITY_THRESHOLD,
            similarity_score=max_similarity,
            matches=[DuplicateMatch(**m) for m in matches],
        )

    # ── Registry Listing ─────────────────────────────────────────

    async def _backfill_language(self, entry: IntakeRegistry) -> None:
        """Recompute and persist language for legacy rows stored before language detection worked."""
        if entry.language_detected or not entry.file_id:
            return
        ext = Path(entry.original_filename).suffix.lower()
        if ext not in (".pdf", ".xml", ".json"):
            return

        ingested = (
            self.db.query(IngestedFile)
            .filter(IngestedFile.id == entry.file_id)
            .first()
        )
        if not ingested or not ingested.storage_path:
            return

        try:
            content_bytes = await self.storage.download_file(ingested.storage_path)
            preprocessing = await asyncio.to_thread(self._preprocess, content_bytes, entry.original_filename, entry.mime_type)
            language_hint = preprocessing.get("language_hint")
            if language_hint:
                entry.language = language_hint
                entry.language_detected = language_hint
                if not entry.page_count and preprocessing.get("page_count"):
                    entry.page_count = preprocessing["page_count"]
                self.db.commit()
        except Exception:
            logger.warning("language_backfill_failed", entry_id=str(entry.id))

    async def list_registry(
        self,
        tenant_id: UUID,
        company_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[IntakeRegistryEntry], int]:
        query = self.db.query(IntakeRegistry).filter(
            IntakeRegistry.tenant_id == tenant_id,
            IntakeRegistry.company_id == company_id,
        )

        if status_filter:
            try:
                status_enum = IntakeStatus(status_filter)
                query = query.filter(IntakeRegistry.status == status_enum)
            except ValueError:
                pass

        if source_filter:
            try:
                channel_enum = SourceChannel(source_filter)
                query = query.filter(IntakeRegistry.source_channel == channel_enum)
            except ValueError:
                pass

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    IntakeRegistry.original_filename.ilike(pattern),
                    IntakeRegistry.checksum.ilike(pattern),
                )
            )

        total = query.count()

        entries = (
            query.order_by(desc(IntakeRegistry.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        for e in entries:
            await self._backfill_language(e)

        return [
            IntakeRegistryEntry(
                id=str(e.id),
                file_id=str(e.file_id) if e.file_id else None,
                original_filename=e.original_filename,
                source_channel=e.source_channel.value if hasattr(e.source_channel, "value") else str(e.source_channel),
                document_type=e.document_type,
                language=e.language,
                status=e.status.value.lower() if hasattr(e.status, "value") else str(e.status).lower(),
                tier=e.tier,
                is_duplicate=e.is_duplicate,
                duplicate_of_id=str(e.duplicate_of_id) if e.duplicate_of_id else None,
                duplicate_similarity=e.duplicate_similarity,
                checksum=e.checksum,
                file_size=e.file_size,
                mime_type=e.mime_type,
                page_count=e.page_count,
                language_detected=e.language_detected,
                orientation=e.orientation,
                processing_metadata=e.processing_metadata,
                created_at=e.created_at,
                processed_at=e.processed_at,
            )
            for e in entries
        ], total

    def get_registry_entry(self, entry_id: UUID, tenant_id: UUID) -> Optional[IntakeRegistryEntry]:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            return None
        # Use the canonical conversion to IntakeRegistryEntry which normalizes
        # status and other presentation details to API-friendly formats.
        return self._to_entry(entry)

    def get_registry_by_file_id(self, file_id: UUID, tenant_id: UUID) -> Optional[IntakeRegistryEntry]:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.file_id == file_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            return None
        # Reuse the canonical conversion which normalizes status/value presentation
        return self._to_entry(entry)

    # ── Preview ─────────────────────────────────────────────────

    async def get_preview(
        self,
        entry_id: UUID,
        tenant_id: UUID,
        page: int = 1,
    ) -> PreviewResponse:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            raise ValueError("Registry entry not found")

        pages: list[dict] = []
        mime_type = entry.mime_type or "application/octet-stream"

        ext = Path(entry.original_filename).suffix.lower()

        total_pages = entry.page_count or 1
        if ext == ".pdf" and not entry.page_count and entry.file_id:
            ingested = (
                self.db.query(IngestedFile)
                .filter(IngestedFile.id == entry.file_id)
                .first()
            )
            if ingested and ingested.storage_path:
                try:
                    content_bytes = await self.storage.download_file(ingested.storage_path)
                    actual_count = await asyncio.to_thread(self._count_pdf_pages, content_bytes)
                    if actual_count:
                        entry.page_count = actual_count
                        self.db.commit()
                        total_pages = actual_count
                except Exception:
                    pass

        for i in range(1, min(total_pages, 20) + 1):
            if entry.file_id:
                image_url = f"/api/v1/data-ingestion/registry/{entry_id}/preview/page/{i}"
            else:
                image_url = ""
            pages.append(
                PreviewPage(
                    page_number=i,
                    image_url=image_url,
                    width=800,
                    height=1050 if ext == ".pdf" else 600,
                )
            )

        return PreviewResponse(
            entry_id=str(entry.id),
            filename=entry.original_filename,
            mime_type=mime_type,
            file_size=entry.file_size,
            total_pages=total_pages,
            pages=pages,
        )

    # ── Extract Navigation ──────────────────────────────────────

    async def prepare_extraction(self, entry_id: UUID, tenant_id: UUID, current_user) -> ExtractNavigationResponse:
        """Called synchronously from the "Open Document Extraction" button.

        Copies the file into the extraction workspace inline, returns the
        `fileId` immediately, and runs Mistral OCR extraction as a detached
        background task — otherwise the user would stare at a blank/frozen
        screen for the entire call instead of watching the pipeline progress
        in real time."""
        from app.modules.frontend_api.store import get_state, scope_for_user

        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            raise ValueError("Registry entry not found")

        if entry.status == IntakeStatus.EXTRACTING:
            raise RuntimeError(
                "Extraction is already in progress for this document. Please wait for it to finish before retrying."
            )

        metadata = entry.processing_metadata or {}
        existing_id = metadata.get("frontend_file_id")
        if existing_id:
            scope = scope_for_user(current_user)
            files = get_state(self.db, scope, "files", [])
            if any(str(f.get("id")) == existing_id for f in files):
                return ExtractNavigationResponse(
                    file_id=existing_id,
                    entry_id=str(entry.id),
                    redirect_url=f"/app/ingestion/data-ingestion/document-extraction?fileId={existing_id}&registryId={entry.id}",
                )

        self._update_status(entry, IntakeStatus.EXTRACTING)
        self._log_event(
            entry.id,
            "extraction_started",
            "processing",
            f"Extraction started: {entry.original_filename}",
        )

        try:
            file_id, path, scope = await self._create_bridge_file_record(entry, current_user)
        except Exception as exc:
            self._update_status(entry, IntakeStatus.FAILED)
            self._log_event(entry.id, "extraction_failed", "failed", f"Extraction pipeline failed: {exc}")
            self.db.commit()
            raise RuntimeError(str(exc)) from exc

        self.db.commit()

        # Background bridge: run Mistral OCR extraction
        asyncio.create_task(_run_mistral_bridge_background(
            entry_id=entry.id,
            tenant_id=tenant_id,
            company_id=entry.company_id,
            file_id=file_id,
            path=str(path),
            scope=scope,
            source_user_id=str(getattr(current_user, "id", "") or "") or None,
        ))

        return ExtractNavigationResponse(
            file_id=file_id,
            entry_id=str(entry.id),
            redirect_url=f"/app/ingestion/data-ingestion/document-extraction?fileId={file_id}&registryId={entry.id}",
        )

    async def _bridge_to_extraction_workspace(self, entry: IntakeRegistry, current_user) -> str:
        """Bridge the intake document to the extraction workspace and run Mistral OCR
        extraction. Used by the auto-extraction background job (already running detached
        from any HTTP request, so it's fine to await the whole thing inline)."""
        metadata = entry.processing_metadata or {}
        from app.modules.frontend_api.store import get_state, scope_for_user
        scope = scope_for_user(current_user)
        files = get_state(self.db, scope, "files", [])
        existing_id = metadata.get("frontend_file_id")
        if existing_id and any(str(f.get("id")) == existing_id for f in files):
            return existing_id

        file_id, path, scope = await self._create_bridge_file_record(entry, current_user)
        self.db.commit()
        await self._run_mistral_extraction(entry, file_id, path, scope)
        return file_id

    async def _create_bridge_file_record(self, entry: IntakeRegistry, current_user) -> tuple[str, Path, str]:
        """Fast part of the bridge: copy the intake document into the extraction
        workspace and create its file record. Does not run Gemini."""
        import hashlib as _hashlib

        from app.modules.frontend_api.document_routes import create_file_record, UPLOAD_ROOT
        from app.modules.frontend_api.store import get_state, set_state, scope_for_user
        from app.modules.frontend_api.utils import safe_filename

        scope = scope_for_user(current_user)
        files = get_state(self.db, scope, "files", [])

        if not entry.file_id:
            raise ValueError("Document has no stored file to extract from")

        ingested = self.db.query(IngestedFile).filter(IngestedFile.id == entry.file_id).first()
        if not ingested or not ingested.storage_path:
            raise ValueError("Stored file not found")

        content = await self.storage.download_file(ingested.storage_path)

        file_id = f"file_{uuid.uuid4().hex[:16]}"
        filename = safe_filename(entry.original_filename)
        mime_type = entry.mime_type or "application/octet-stream"
        scope_dir = UPLOAD_ROOT / _hashlib.sha256(scope.encode()).hexdigest()[:16]
        scope_dir.mkdir(parents=True, exist_ok=True)
        path = scope_dir / f"{file_id}_{filename}"
        path.write_bytes(content)

        record = create_file_record(
            file_id,
            filename,
            mime_type,
            len(content),
            _hashlib.sha256(content).hexdigest(),
            str(path),
            current_user,
        )
        record["status"] = "processing"
        record["processingStage"] = "Preprocessing"
        record["intakeRegistryId"] = str(entry.id)
        files.insert(0, record)
        set_state(self.db, scope, "files", files)

        metadata = entry.processing_metadata or {}
        entry.processing_metadata = {**metadata, "frontend_file_id": file_id}

        return file_id, path, scope

    async def _run_mistral_extraction(self, entry: IntakeRegistry, file_id: str, path: Path, scope: str) -> None:
        """Run extraction using Mistral OCR and deterministic field extraction."""
        from app.modules.extraction.adapters.mistral_fallback import MistralFallbackExtractor
        from app.modules.frontend_api.store import get_state, set_state
        from app.modules.frontend_api.utils import now_iso, new_id
        from app.modules.frontend_api.business_validators import validate_all
        from app.modules.frontend_api.json_export_service import build_extraction_json, store_extraction_json
        from app.modules.frontend_api.document_intelligence import processing_validation_issues

        live_files = get_state(self.db, scope, "files", [])
        record = next((dict(f) for f in live_files if str(f.get("id")) == file_id), None)
        if record is None:
            raise RuntimeError("Workspace file record not found")

        def _save_progress(stage: str, extraction_progress: dict | None = None) -> None:
            record["processingStage"] = stage
            if extraction_progress is not None:
                record["extractionProgress"] = extraction_progress
            live = get_state(self.db, scope, "files", [])
            for i, f in enumerate(live):
                if str(f.get("id")) == file_id:
                    live[i] = dict(record)
                    break
            set_state(self.db, scope, "files", live)

        _save_progress("Document Analysis")

        try:
            extractor = MistralFallbackExtractor()
            extraction_result = await asyncio.to_thread(extractor.extract, Path(path), True, True, document_type=entry.document_type)

            metadata = extraction_result.metadata or {}
            extracted_fields_raw = metadata.get("extracted_fields", {})
            field_conf = metadata.get("field_confidence", {})
            overall_confidence = float(extraction_result.confidence or 0.0)

            def _map_fields(raw: dict) -> dict:
                mapping = {
                    "invoice_number": "invoiceNumber",
                    "invoice_date": "invoiceDate",
                    "due_date": "dueDate",
                    "vendor_name": "vendor",
                    "vendor_address": "vendorAddress",
                    "vendor_phone": "vendorPhone",
                    "vendor_email": "vendorEmail",
                    "vendor_pan": "vendorPan",
                    "customer_name": "customer",
                    "customer_gstin": "customerGstin",
                    "customer_address": "customerAddress",
                    "customer_phone": "customerPhone",
                    "customer_email": "customerEmail",
                    "customer_pan": "customerPan",
                    "gst_vat_number": "gstVatNumber",
                    "currency": "currency",
                    "subtotal": "subtotal",
                    "tax_total": "taxAmount",
                    "total_amount": "total",
                    "line_items": "lineItems",
                    "cgst_amount": "cgstAmount",
                    "sgst_amount": "sgstAmount",
                    "igst_amount": "igstAmount",
                    "taxable_value": "taxableValue",
                    "gross_amount": "grossAmount",
                    "discount_amount": "discountAmount",
                    "place_of_supply": "placeOfSupply",
                    "reverse_charge": "reverseCharge",
                    "tax_rates": "taxRates",
                    "tax_rate": "taxRate",
                    "reference_number": "referenceNumber",
                    "bank_name": "bankName",
                    "branch_name": "branchName",
                    "account_holder_name": "accountHolderName",
                    "account_number": "accountNumber",
                    "account_type": "accountType",
                    "statement_period_from": "statementPeriodFrom",
                    "statement_period_to": "statementPeriodTo",
                    "opening_balance": "openingBalance",
                    "closing_balance": "closingBalance",
                    "transactions": "transactions",
                    "ifsc_swift_code": "ifscSwiftCode",
                    "iban": "iban",
                    "amount": "amount",
                    "remittance_details": "remittanceDetails",
                    "exporter": "exporter",
                    "importer": "importer",
                    "buyer": "buyer",
                    "seller": "seller",
                    "incoterms": "incoterms",
                    "country_of_origin": "countryOfOrigin",
                    "country_of_destination": "countryOfDestination",
                    "port_of_loading": "portOfLoading",
                    "port_of_discharge": "portOfDischarge",
                    "gross_weight": "grossWeight",
                    "net_weight": "netWeight",
                    "payment_terms": "paymentTerms",
                    "invoice_value": "invoiceValue",
                    "vendor": "vendor",
                    "customer": "customer",
                    # Identity mappings for camelCase keys from GLiNER/LayoutLMv3 enrichments
                    "vendorAddress": "vendorAddress",
                    "customerAddress": "customerAddress",
                    "invoiceNumber": "invoiceNumber",
                    "invoiceDate": "invoiceDate",
                    "dueDate": "dueDate",
                    "gstVatNumber": "gstVatNumber",
                    "vendorPan": "vendorPan",
                    "vendorPhone": "vendorPhone",
                    "vendorEmail": "vendorEmail",
                    "total": "total",
                    "subtotal": "subtotal",
                    "taxAmount": "taxAmount",
                    "cgstAmount": "cgstAmount",
                    "sgstAmount": "sgstAmount",
                    "igstAmount": "igstAmount",
                    "taxRate": "taxRate",
                    "discountAmount": "discountAmount",
                    "placeOfSupply": "placeOfSupply",
                    "reverseCharge": "reverseCharge",
                }
                out = {}
                for k, v in raw.items():
                    dest = mapping.get(k)
                    if dest:
                        out[dest] = v
                # Remap line-item inner dict keys from snake_case to camelCase
                line_items = out.get("lineItems")
                if line_items and isinstance(line_items, list):
                    item_mapping = {
                        "description": "productName",
                        "hsn_code": "hsnCode",
                        "batch_number": "batchNumber",
                        "expiry_date": "expiryDate",
                        "line_total": "lineTotal",
                    }
                    remapped = []
                    for item in line_items:
                        if isinstance(item, dict):
                            new_item = dict(item)
                            for src, dst in item_mapping.items():
                                if src in new_item and dst not in new_item:
                                    new_item[dst] = new_item[src]
                            remapped.append(new_item)
                        else:
                            remapped.append(item)
                    out["lineItems"] = remapped
                return out

            fields = _map_fields(extracted_fields_raw)
            # Attach a synthetic per-field confidence structure compatible with downstream
            gemini_field_confidence = {}
            for k, v in field_conf.items():
                # map keys similarly to fields mapping
                mapped_key = {
                    "invoice_number": "invoiceNumber",
                    "invoice_date": "invoiceDate",
                    "vendor_name": "vendor",
                    "customer_name": "customer",
                    "total_amount": "total",
                }.get(k, None)
                if mapped_key:
                    gemini_field_confidence[mapped_key] = float(v or overall_confidence)

            dtype = metadata.get("document_type") or entry.document_type or "other"
            fields["documentType"] = dtype
            record.update({
                "status": "processing",
                "ocrStatus": "completed",
                "extractionStatus": "completed",
                "entriesExtracted": 1,
                "confidence": overall_confidence,
                "sourceLanguage": entry.language or "Unknown",
                "extractionMethod": "mistral",
                "extractionConfidence": overall_confidence,
                "fieldConfidence": gemini_field_confidence,
                "extractedText": (extraction_result.text or "")[:100_000],
                "extractedTables": extraction_result.tables,
                "structuredFields": fields,
                "amount": fields.get("total") or fields.get("amount") or 0,
                "currency": fields.get("currency") or "USD",
                "vendor": fields.get("vendor"),
                "customer": fields.get("customer"),
                "invoiceNumber": fields.get("invoiceNumber"),
                "invoiceDate": fields.get("invoiceDate"),
                "lineItems": fields.get("lineItems") or [],
                "category": dtype,
                "classificationReason": "Classified by Mistral fallback",
                # Banking fields
                "bankName": fields.get("bankName"),
                "branchName": fields.get("branchName"),
                "accountHolderName": fields.get("accountHolderName"),
                "accountNumber": fields.get("accountNumber"),
                "accountType": fields.get("accountType"),
                "statementPeriodFrom": fields.get("statementPeriodFrom"),
                "statementPeriodTo": fields.get("statementPeriodTo"),
                "openingBalance": fields.get("openingBalance"),
                "closingBalance": fields.get("closingBalance"),
                "transactions": fields.get("transactions") or [],
                # Trade fields
                "exporter": fields.get("exporter"),
                "importer": fields.get("importer"),
                "buyer": fields.get("buyer"),
                "seller": fields.get("seller"),
                "incoterms": fields.get("incoterms"),
                "countryOfOrigin": fields.get("countryOfOrigin"),
                "countryOfDestination": fields.get("countryOfDestination"),
                "portOfLoading": fields.get("portOfLoading"),
                "portOfDischarge": fields.get("portOfDischarge"),
                "grossWeight": fields.get("grossWeight"),
                "netWeight": fields.get("netWeight"),
                "paymentTerms": fields.get("paymentTerms"),
                "invoiceValue": fields.get("invoiceValue"),
                "referenceNumber": fields.get("referenceNumber"),
                "dueDate": fields.get("dueDate"),
                "ocr": {
                    "engine": "mistral_ocr", "engineVersion": metadata.get("model"),
                    "status": "completed", "languageDetected": entry.language or "Unknown",
                    "overallConfidence": overall_confidence, "pageCount": extraction_result.page_count,
                    "startedAt": now_iso(), "completedAt": now_iso(),
                },
                "processingCompletedAt": now_iso(),
            })

            _save_progress("Field Extraction", {"totalPages": extraction_result.page_count or 1, "currentStage": "extracted"})

            # Validation
            record["validationResults"] = validate_all(fields)
            record["validationIssues"] = processing_validation_issues(record)
            has_error_issues = any(issue.get("severity") == "error" for issue in record["validationIssues"]) if record.get("validationIssues") else False

            review_reasons = []
            for item in record["validationResults"].get("needs_review", []):
                if item.get("message"):
                    review_reasons.append(f"Validation: {item['message']}")
            for item in record["validationResults"].get("warning", []):
                if item.get("message"):
                    review_reasons.append(f"Validation warning: {item['message']}")
            if has_error_issues:
                review_reasons.extend(issue["message"] for issue in record.get("validationIssues", []) if issue.get("severity") == "error")

            record["reviewReasons"] = review_reasons
            record["status"] = "validation_failed" if has_error_issues else ("needs_review" if review_reasons else "completed")

            try:
                extraction_json = build_extraction_json(record, fields)
                record["extractionJson"] = extraction_json.model_dump_export()
                store_extraction_json(self.db, scope, file_id, extraction_json)
            except Exception as json_err:
                logger.warning("mistral_extraction_json_failed", entry_id=str(entry.id), error=str(json_err))

            record["processingStage"] = "Extraction Complete" if record["status"] in ("completed", "needs_review") else record["status"]
            record["extractionProgress"] = {"totalPages": extraction_result.page_count or 1, "currentStage": "extracted"}
            _save_progress(record["processingStage"], record["extractionProgress"])

            logger.info("mistral_extraction_bridge_complete", entry_id=str(entry.id), file_id=file_id, confidence=overall_confidence)

        except Exception as exc:
            logger.warning("mistral_extraction_bridge_failed", entry_id=str(entry.id), error=str(exc))
            record.update({
                "status": "validation_failed",
                "ocrStatus": "failed",
                "extractionStatus": "failed",
            })
            _save_progress(record.get("processingStage", "Field Extraction"), {"currentStage": "extraction_failed", "error": str(exc)})
            message = str(exc)
            raise RuntimeError(message)

        self.db.commit()

    def _purge_extraction_workspace(self, entry: IntakeRegistry, current_user) -> None:
        """Remove the bridged extraction-workspace record (and everything derived
        from it: entries, review tasks, postings, extraction JSON) so a document
        deleted from the intake registry stops counting on the dashboard.

        Mirrors the cleanup in frontend_api.document_routes.delete_file — kept in
        sync manually since the two stores are independent."""
        metadata = entry.processing_metadata or {}
        file_id = metadata.get("frontend_file_id")
        if not file_id:
            return

        from app.modules.frontend_api.json_export_service import delete_extraction_json
        from app.modules.frontend_api.store import get_state, set_state, scope_for_user

        scope = scope_for_user(current_user)
        files = get_state(self.db, scope, "files", [])
        item = next((f for f in files if str(f.get("id")) == str(file_id)), None)
        if item is None:
            return

        content_path = Path(str(item.get("_contentPath") or ""))
        files = [f for f in files if str(f.get("id")) != str(file_id)]
        set_state(self.db, scope, "files", files)

        entries = get_state(self.db, scope, "entries", [])
        removed_entry_ids = [str(e.get("id")) for e in entries if str(e.get("fileId")) == str(file_id)]
        entries = [e for e in entries if str(e.get("fileId")) != str(file_id)]
        set_state(self.db, scope, "entries", entries)

        tasks = get_state(self.db, scope, "review_tasks", [])
        set_state(self.db, scope, "review_tasks", [t for t in tasks if str((t.get("entry") or {}).get("fileId")) != str(file_id)])

        postings = get_state(self.db, scope, "sap_postings", [])
        set_state(self.db, scope, "sap_postings", [p for p in postings if str(p.get("entryId")) not in removed_entry_ids])

        delete_extraction_json(self.db, scope, file_id)

        try:
            if content_path.exists():
                content_path.unlink()
        except OSError:
            pass

    # ── Hard Delete ──────────────────────────────────────────────

    async def bulk_hard_delete(self, entry_ids: List[UUID], tenant_id: UUID, current_user=None) -> dict:
        deleted = 0
        for entry_id in entry_ids:
            try:
                await self.hard_delete(entry_id, tenant_id, current_user)
                deleted += 1
            except ValueError:
                continue
        return {"deleted": deleted, "message": f"{deleted} of {len(entry_ids)} documents permanently deleted"}

    async def hard_delete(self, entry_id: UUID, tenant_id: UUID, current_user=None) -> DeleteResponse:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            raise ValueError("Registry entry not found")

        if current_user is not None:
            self._purge_extraction_workspace(entry, current_user)

        file_id = entry.file_id

        if file_id:
            try:
                actual_records = self.tiered.get_tier_records(file_id)
                for rec in actual_records:
                    try:
                        await self.storage.delete_file(rec.storage_key)
                    except Exception:
                        pass
                    self.db.delete(rec)

                # Delete document embedding
                embedding = (
                    self.db.query(DocumentEmbedding)
                    .filter(DocumentEmbedding.file_id == file_id)
                    .first()
                )
                if embedding:
                    try:
                        await self.storage.delete_file(embedding.embedding_path)
                    except Exception:
                        pass
                    self.db.delete(embedding)

                # Delete processing audit records
                from app.modules.ingestion.tiered_storage import ProcessingAudit
                audits = (
                    self.db.query(ProcessingAudit)
                    .filter(ProcessingAudit.file_id == file_id)
                    .all()
                )
                for a in audits:
                    self.db.delete(a)

                # Delete ingested file record (and cascade to storage)
                ingested = (
                    self.db.query(IngestedFile)
                    .filter(IngestedFile.id == file_id)
                    .first()
                )
                if ingested:
                    try:
                        await self.storage.delete_file(ingested.storage_path)
                    except Exception:
                        pass
                    self.db.delete(ingested)

                # Delete extraction/OCR/translation results by file_id
                for model_cls in self._get_related_models():
                    records = self.db.query(model_cls).filter(model_cls.file_id == file_id).all()
                    for r in records:
                        self.db.delete(r)

            except Exception as exc:
                logger.error("delete_cascade_failed", file_id=str(file_id), error=str(exc))

        # Log deletion event before deleting the entry
        self._log_event(
            entry.id,
            "delete",
            "completed",
            f"Document permanently deleted: {entry.original_filename}",
        )

        # Delete events and registry entry
        events = self.db.query(IntakeEvent).filter(IntakeEvent.registry_id == entry.id).all()
        for ev in events:
            self.db.delete(ev)

        self.db.delete(entry)
        self.db.commit()

        return DeleteResponse(
            deleted=True,
            message=f"Document '{entry.original_filename}' and all associated records permanently deleted",
        )

    def _get_related_models(self):
        models = []
        try:
            from app.modules.extraction.models import FileExtractionResult
            models.append(FileExtractionResult)
        except ImportError:
            pass
        try:
            from app.modules.ocr.models import OCRResult
            models.append(OCRResult)
        except ImportError:
            pass
        return models

    # ── Events ──────────────────────────────────────────────────

    def get_events(self, entry_id: UUID, tenant_id: UUID) -> List[IntakeEventResponse]:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            raise ValueError("Registry entry not found")

        events = (
            self.db.query(IntakeEvent)
            .filter(IntakeEvent.registry_id == entry.id)
            .order_by(IntakeEvent.created_at)
            .all()
        )
        return [
            IntakeEventResponse(
                id=str(e.id),
                registry_id=str(e.registry_id),
                event_type=e.event_type,
                status=e.status,
                message=e.message,
                metadata_json=e.metadata_json,
                created_at=e.created_at,
            )
            for e in events
        ]

    # ── Status Update ────────────────────────────────────────────

    def update_status(self, entry_id: UUID, tenant_id: UUID, status: IntakeStatus) -> IntakeRegistryEntry:
        entry = (
            self.db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            raise ValueError("Registry entry not found")

        self._update_status(entry, status)
        self._log_event(entry.id, "status_change", status.value, f"Status changed to {status.value}")

        return IntakeRegistryEntry(
            id=str(entry.id),
            file_id=str(entry.file_id) if entry.file_id else None,
            original_filename=entry.original_filename,
            source_channel=entry.source_channel.value if hasattr(entry.source_channel, "value") else str(entry.source_channel),
            document_type=entry.document_type,
            language=entry.language,
            status=entry.status.value if hasattr(entry.status, "value") else str(entry.status),
            tier=entry.tier,
            is_duplicate=entry.is_duplicate,
            duplicate_of_id=str(entry.duplicate_of_id) if entry.duplicate_of_id else None,
            duplicate_similarity=entry.duplicate_similarity,
            checksum=entry.checksum,
            file_size=entry.file_size,
            mime_type=entry.mime_type,
            page_count=entry.page_count,
            language_detected=entry.language_detected,
            orientation=entry.orientation,
            processing_metadata=entry.processing_metadata,
            created_at=entry.created_at,
            processed_at=entry.processed_at,
        )


def _resolve_bridge_user(db: Session, tenant_id: UUID, company_id: Optional[UUID], source_user_id: Optional[str]):
    """Re-resolve the acting user inside a detached background task, which
    can't reuse the request-scoped user object from `prepare_extraction`."""
    from app.modules.users.models import User
    if source_user_id:
        try:
            user = db.query(User).filter(User.id == UUID(source_user_id)).first()
            if user:
                return user
        except ValueError:
            pass
    from types import SimpleNamespace
    return SimpleNamespace(
        id=source_user_id or str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id or tenant_id,
        is_super_admin=False,
        email="system@translatrix.ai",
        full_name="System Worker",
    )


async def _run_mistral_bridge_background(
    *,
    entry_id: UUID,
    tenant_id: UUID,
    company_id: Optional[UUID],
    file_id: str,
    path: str,
    scope: str,
    source_user_id: Optional[str],
) -> None:
    """Detached background task for the manual "Open Document Extraction"
    button: runs Mistral OCR extraction after `prepare_extraction` has already
    returned the fileId to the caller.

    Opens its own DB session since the request's session closes as soon as the
    HTTP response is sent.
    """
    from app.database import SessionLocal
    from app.modules.storage.service import get_storage_adapter

    db = SessionLocal()
    try:
        entry = (
            db.query(IntakeRegistry)
            .filter(IntakeRegistry.id == entry_id, IntakeRegistry.tenant_id == tenant_id)
            .first()
        )
        if not entry:
            logger.warning("bridge_background_entry_missing", entry_id=str(entry_id))
            return

        storage = await get_storage_adapter()
        service = DataIntakeService(db, storage)
        user = _resolve_bridge_user(db, tenant_id, company_id, source_user_id)

        try:
            await service._run_mistral_extraction(entry, file_id, Path(path), scope)
            service._update_status(entry, IntakeStatus.EXTRACTED)
            service._log_event(
                entry.id, "extraction_completed", "completed",
                f"Mistral OCR extraction completed: {entry.original_filename}",
            )
        except Exception as exc:
            service._update_status(entry, IntakeStatus.FAILED)
            service._log_event(entry.id, "extraction_failed", "failed", f"Extraction pipeline failed: {exc}")
            logger.warning("bridge_background_failed", entry_id=str(entry_id), error=str(exc))
        db.commit()
    finally:
        db.close()
