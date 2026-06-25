"""
Ingestion Service
File ingestion orchestration and batch management
"""
import hashlib
import json
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
import structlog
from uuid import UUID

from app.modules.ingestion.models import (
    SharedLinkSource,
    IngestionBatch,
    IngestedFile,
    IngestionSource,
    BatchStatus,
    FileStatus,
)
from app.modules.ingestion.schemas import (
    SharedLinkValidateResponse,
    SharedLinkResponse,
    BatchResponse,
    DiscoveredFile,
    FileDiscoveryResponse,
    IngestionSourceType,
    ExtractionResult,
    ExtractedField,
)
from app.modules.ingestion.connectors import (
    BaseConnector,
    GoogleDriveConnector,
    OneDriveConnector,
    S3Connector,
    LocalUploadConnector,
)
from app.config import settings
from app.modules.storage.adapters.base import BaseStorage

logger = structlog.get_logger(__name__)


class IngestionService:
    """Service for file ingestion operations"""

    def __init__(self, db: Session):
        self.db = db

    def _get_connector(self, source_type: str, config: Dict[str, Any]) -> BaseConnector:
        """
        Get appropriate connector for source type
        """
        connector_map = {
            "google_drive": GoogleDriveConnector,
            "onedrive": OneDriveConnector,
            "sharepoint": OneDriveConnector,  # SharePoint uses OneDrive connector
            "aws_s3": S3Connector,
            "local_upload": LocalUploadConnector,
        }

        connector_class = connector_map.get(source_type)
        if not connector_class:
            raise ValueError(f"Unsupported source type: {source_type}")

        return connector_class(config)

    async def validate_shared_link(
        self,
        url: str,
        source_type: IngestionSourceType,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> SharedLinkValidateResponse:
        """
        Validate a shared link and check accessibility
        """
        logger.info("validating_shared_link", source_type=source_type, url=url)

        try:
            # Build connector config
            config = {
                "url": url,
                "credentials": credentials,
            }

            connector = self._get_connector(source_type.value, config)

            # Validate connection
            is_valid = await connector.validate_connection()

            if not is_valid:
                return SharedLinkValidateResponse(
                    is_valid=False,
                    source_type=source_type,
                    error_message="Failed to validate connection",
                )

            # Try to list files to get count and size
            try:
                files = await connector.list_files()
                file_count = len(files)
                total_size = sum(f.size for f in files)

                return SharedLinkValidateResponse(
                    is_valid=True,
                    source_type=source_type,
                    file_count=file_count,
                    total_size_bytes=total_size,
                )
            except:
                # Connection valid but couldn't list files
                return SharedLinkValidateResponse(
                    is_valid=True,
                    source_type=source_type,
                    file_count=None,
                    total_size_bytes=None,
                )

        except Exception as e:
            logger.error("shared_link_validation_failed", error=str(e))
            return SharedLinkValidateResponse(
                is_valid=False,
                source_type=source_type,
                error_message=str(e),
            )

    def create_shared_link_source(
        self,
        tenant_id: UUID,
        company_id: UUID,
        name: str,
        source_type: IngestionSourceType,
        url: Optional[str] = None,
        credentials: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> SharedLinkSource:
        """
        Create a new shared link source
        """
        logger.info(
            "creating_shared_link_source",
            tenant_id=str(tenant_id),
            company_id=str(company_id),
            source_type=source_type,
        )

        # Convert enum to IngestionSource enum
        source_enum = IngestionSource[source_type.name]

        source = SharedLinkSource(
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            source_type=source_enum,
            url=url,
            credentials=credentials,  # Should be encrypted before storing
            config=config,
            is_active=True,
        )

        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        logger.info("shared_link_source_created", source_id=str(source.id))
        return source

    def list_shared_link_sources(
        self, tenant_id: UUID, company_id: UUID
    ) -> Tuple[List[SharedLinkSource], int]:
        """
        List all shared link sources for a company
        """
        query = self.db.query(SharedLinkSource).filter(
            SharedLinkSource.tenant_id == tenant_id,
            SharedLinkSource.company_id == company_id,
        )

        total = query.count()
        sources = query.order_by(desc(SharedLinkSource.created_at)).all()

        return sources, total

    def get_shared_link_source(
        self, source_id: UUID, tenant_id: UUID
    ) -> Optional[SharedLinkSource]:
        """
        Get a specific shared link source
        """
        return (
            self.db.query(SharedLinkSource)
            .filter(
                SharedLinkSource.id == source_id,
                SharedLinkSource.tenant_id == tenant_id,
            )
            .first()
        )

    async def sync_shared_link(
        self,
        source_id: UUID,
        tenant_id: UUID,
        file_types: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> FileDiscoveryResponse:
        """
        Sync files from a shared link source
        """
        logger.info("syncing_shared_link", source_id=str(source_id))

        source = self.get_shared_link_source(source_id, tenant_id)
        if not source:
            raise ValueError("Shared link source not found")

        # Build connector config
        config = {
            "url": source.url,
            "credentials": source.credentials,  # Should be decrypted
            **(source.config or {}),
        }

        connector = self._get_connector(source.source_type.value, config)

        # List files from source
        files = await connector.list_files(recursive=recursive, file_types=file_types)

        # Convert to discovered files
        discovered = [
            DiscoveredFile(
                name=f.name,
                path=f.path,
                size=f.size,
                mime_type=f.mime_type,
                modified_at=f.modified_at,
                source_id=f.source_id,
            )
            for f in files
        ]

        total_size = sum(f.size for f in discovered)

        # Update last synced timestamp
        source.last_synced_at = datetime.utcnow()
        self.db.commit()

        return FileDiscoveryResponse(
            files=discovered,
            total_count=len(discovered),
            total_size_bytes=total_size,
        )

    def create_batch(
        self,
        tenant_id: UUID,
        company_id: UUID,
        source_id: Optional[UUID] = None,
        batch_name: Optional[str] = None,
    ) -> IngestionBatch:
        """
        Create a new ingestion batch
        """
        logger.info(
            "creating_batch",
            tenant_id=str(tenant_id),
            company_id=str(company_id),
            source_id=str(source_id) if source_id else None,
        )

        batch = IngestionBatch(
            tenant_id=tenant_id,
            company_id=company_id,
            source_id=source_id,
            batch_name=batch_name or f"Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            status=BatchStatus.PENDING,
            total_files=0,
            processed_files=0,
            failed_files=0,
        )

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        logger.info("batch_created", batch_id=str(batch.id))
        return batch

    def list_batches(
        self, tenant_id: UUID, company_id: UUID, page: int = 1, page_size: int = 50
    ) -> Tuple[List[IngestionBatch], int]:
        """
        List batches for a company
        """
        query = self.db.query(IngestionBatch).filter(
            IngestionBatch.tenant_id == tenant_id,
            IngestionBatch.company_id == company_id,
        )

        total = query.count()

        batches = (
            query.order_by(desc(IngestionBatch.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return batches, total

    def get_batch(self, batch_id: UUID, tenant_id: UUID) -> Optional[IngestionBatch]:
        """
        Get a specific batch
        """
        return (
            self.db.query(IngestionBatch)
            .filter(
                IngestionBatch.id == batch_id,
                IngestionBatch.tenant_id == tenant_id,
            )
            .first()
        )

    def get_batch_files(self, batch_id: UUID, tenant_id: UUID) -> List[IngestedFile]:
        """
        Get all files in a batch
        """
        return (
            self.db.query(IngestedFile)
            .filter(
                IngestedFile.batch_id == batch_id,
                IngestedFile.tenant_id == tenant_id,
            )
            .order_by(IngestedFile.created_at)
            .all()
        )

    def update_batch_status(
        self, batch_id: UUID, status: BatchStatus, completed_at: Optional[datetime] = None
    ) -> bool:
        """
        Update batch status
        """
        batch = self.db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
        if not batch:
            return False

        batch.status = status
        batch.updated_at = datetime.utcnow()
        if completed_at:
            batch.completed_at = completed_at

        self.db.commit()
        return True

    async def generate_preview(
        self,
        file_record: IngestedFile,
        storage: BaseStorage,
        page: int = 1,
        max_pages: int = 10,
    ) -> Dict[str, Any]:
        ext = (file_record.original_filename or "").lower().rsplit(".", 1)[-1] if "." in (file_record.original_filename or "") else ""
        content_bytes = b""
        if file_record.storage_path:
            try:
                content_bytes = await storage.download_file(file_record.storage_path)
            except Exception:
                pass

        total_pages = 1
        rendered_pages: List[Dict[str, Any]] = []

        if ext == "pdf":
            total_pages = self._count_pdf_pages(content_bytes)
            for i in range(1, min(total_pages, max_pages) + 1):
                rendered_pages.append({
                    "pageNumber": i,
                    "imageUrl": f"/api/v1/files/{file_record.id}/preview/page/{i}",
                    "width": 800,
                    "height": 1050,
                })
        elif ext in {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}:
            rendered_pages.append({
                "pageNumber": 1,
                "imageUrl": f"/api/v1/files/{file_record.id}/preview/page/1",
                "width": 800,
                "height": 600,
            })
        else:
            rendered_pages.append({
                "pageNumber": 1,
                "imageUrl": f"/api/v1/files/{file_record.id}/preview/page/1",
                "width": 800,
                "height": 600,
            })

        return {
            "totalPages": total_pages,
            "pages": rendered_pages,
            "contentBytes": content_bytes,
        }

    def _count_pdf_pages(self, content: bytes) -> int:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(content)
            return len(reader.pages)
        except Exception:
            return 1

    async def extract_fields(
        self,
        file_record: IngestedFile,
        storage: BaseStorage,
        tenant_id: UUID,
        company_id: UUID,
    ) -> ExtractionResult:
        import time
        started = time.time()
        content_bytes = b""
        if file_record.storage_path:
            try:
                content_bytes = await storage.download_file(file_record.storage_path)
            except Exception:
                pass

        ocr_engine = "mistral_ocr"
        raw_text = ""
        fields: List[Dict[str, Any]] = []

        try:
            from app.modules.ocr.adapters.mistral_adapter import MistralOCRProvider

            mistral_provider = MistralOCRProvider({
                "api_key": settings.MISTRAL_API_KEY,
                "model": settings.MISTRAL_OCR_MODEL,
            })

            if not content_bytes:
                raise ValueError("No file content available for OCR")

            suffix = ""
            if file_record.file_type:
                suffix = f".{file_record.file_type.strip('.')}"
            elif file_record.original_filename:
                suffix = Path(file_record.original_filename).suffix

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".bin") as tmp:
                tmp.write(content_bytes)
                tmp_path = Path(tmp.name)

            try:
                if (file_record.mime_type or "").lower() == "application/pdf" or (file_record.file_type or "").lower() == "pdf":
                    ocr_result = mistral_provider.recognize_pdf(tmp_path)
                    raw_text = ocr_result.full_text
                    for page in ocr_result.pages:
                        fields.append({
                            "name": "ocr_page",
                            "value": page.text,
                            "confidence": page.confidence,
                            "pageNumber": page.page_number,
                            "bbox": None,
                        })
                else:
                    page_result = mistral_provider.recognize_image(tmp_path)
                    raw_text = page_result.text
                    fields.append({
                        "name": "ocr_page",
                        "value": page_result.text,
                        "confidence": page_result.confidence,
                        "pageNumber": page_result.page_number,
                        "bbox": None,
                    })
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            ocr_engine = "fallback_raw"
            logger.warning("mistral_extraction_failed", file_id=str(file_record.id), error=str(exc))
            raw_text = content_bytes.decode("utf-8", errors="replace")[:50000]
            fields.append({
                "name": "raw_text",
                "value": raw_text[:2000],
                "confidence": 0.5,
                "pageNumber": 1,
            })

        structured = self._extract_structured_fields(raw_text, fields)
        confidence = sum(f.get("confidence", 0) for f in structured) / max(len(structured), 1)

        processing_time = int((time.time() - started) * 1000)

        from app.modules.frontend_api.events import append_processing_log
        try:
            append_processing_log(self.db, str(file_record.id), "extraction", {
                "ocr_engine": ocr_engine,
                "fields_count": len(structured),
                "confidence": round(confidence, 4),
                "processing_time_ms": processing_time,
            })
        except Exception:
            pass

        return ExtractionResult(
            fileId=str(file_record.id),
            filename=file_record.original_filename or "unknown",
            fields=[ExtractedField(**f) for f in structured],
            rawText=raw_text[:50000],
            confidence=round(confidence, 4),
            processingTimeMs=processing_time,
            ocrEngine=ocr_engine,
        )

    def _extract_structured_fields(
        self, raw_text: str, ocr_lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        fields: List[Dict[str, Any]] = []
        seen: set = set()
        text_lower = raw_text.lower()

        patterns: Dict[str, List[str]] = {
            "invoice_number": ["invoice", "factura", "inv", "invoice #", "invoice no"],
            "vendor_name": ["vendor", "supplier", "proveedor", "seller", "from"],
            "vendor_address": ["address", "direction", "calle", "addr"],
            "customer_name": ["customer", "client", "cliente", "bill to", "buyer"],
            "customer_address": ["ship to", "deliver to", "remitente"],
            "invoice_date": ["date", "fecha", "issued", "dated"],
            "due_date": ["due", "vencimiento", "payment due"],
            "total_amount": ["total", "amount due", "total due", "importe", "total a pagar", "balance due"],
            "subtotal": ["subtotal", "sub-total", "base"],
            "tax_amount": ["tax", "iva", "vat", "gst", "impuesto"],
            "currency": ["currency", "moneda", "eur", "usd"],
            "purchase_order": ["po", "purchase order", "order no", "reference"],
            "payment_terms": ["terms", "payment terms", "condiciones"],
            "iban": ["iban", "bank account"],
            "swift": ["swift", "bic"],
        }

        for field_name, keywords in patterns.items():
            for kw in keywords:
                idx = text_lower.find(kw)
                if idx >= 0:
                    snippet = raw_text[idx:idx + 120].split("\n")[0].strip()
                    value = snippet[len(kw):].strip().lstrip(":#- \t")
                    if value and field_name not in seen:
                        confidence = 0.85 if idx < 500 else 0.7
                        fields.append({
                            "name": field_name,
                            "value": value[:200],
                            "confidence": confidence,
                            "pageNumber": 1,
                        })
                        seen.add(field_name)
                    break

        for line in ocr_lines:
            candidate = line.get("value", "").strip()
            if len(candidate) > 3 and candidate not in seen:
                fields.append({
                    "name": line.get("name", "ocr_line"),
                    "value": candidate[:200],
                    "confidence": line.get("confidence", 0.5),
                    "pageNumber": line.get("pageNumber", 1),
                    "bbox": line.get("bbox"),
                })
                seen.add(candidate)

        return fields[:50]

    async def export_files(
        self,
        file_ids: List[UUID],
        tenant_id: UUID,
        storage: BaseStorage,
        include_raw_text: bool = True,
        include_metadata: bool = True,
        include_confidence: bool = False,
    ) -> Dict[str, Any]:
        files_data: List[Dict[str, Any]] = []

        for fid in file_ids:
            file_record = self.db.query(IngestedFile).filter(
                IngestedFile.id == fid,
                IngestedFile.tenant_id == tenant_id,
            ).first()
            if not file_record:
                continue

            result = await self.extract_fields(file_record, storage, tenant_id, file_record.company_id or tenant_id)
            file_entry: Dict[str, Any] = {
                "fileId": str(fid),
                "filename": file_record.original_filename or "unknown",
                "extractedAt": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {
                        "name": f.name,
                        "value": f.value,
                        "confidence": f.confidence if include_confidence else None,
                        "pageNumber": f.pageNumber,
                    }
                    for f in result.fields
                ],
            }

            if include_raw_text:
                file_entry["rawText"] = result.rawText[:20000]

            if include_metadata:
                file_entry["metadata"] = {
                    "fileSize": file_record.file_size,
                    "contentType": file_record.content_type,
                    "checksum": file_record.checksum,
                    "createdAt": file_record.created_at.isoformat() if file_record.created_at else None,
                    "status": file_record.status.value if hasattr(file_record.status, 'value') else str(file_record.status),
                }

            files_data.append(file_entry)

        return {"files": files_data}
