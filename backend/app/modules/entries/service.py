"""Entries Service"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from app.modules.entries.models import FinancialEntry, EntryStatus
from app.modules.entries.extractors.invoice_extractor import InvoiceExtractor
from app.modules.entries.extractors.receipt_extractor import ReceiptExtractor
from app.modules.entries.extractors.spreadsheet_extractor import SpreadsheetExtractor
from app.modules.extraction.models import FileExtractionResult

logger = structlog.get_logger(__name__)


class EntriesService:
    """Financial entries extraction and management"""

    def __init__(self):
        self.invoice_extractor = InvoiceExtractor()
        self.receipt_extractor = ReceiptExtractor()
        self.spreadsheet_extractor = SpreadsheetExtractor()

    def extract_entries_from_file(
        self, db: Session, file_id: UUID, tenant_id: UUID, batch_id: UUID
    ) -> List[FinancialEntry]:
        """Extract financial entries from file"""
        # Get extraction result
        extraction = db.query(FileExtractionResult).filter(
            FileExtractionResult.file_id == file_id,
            FileExtractionResult.tenant_id == tenant_id,
        ).first()

        if not extraction:
            raise ValueError("File must be extracted first")

        entries_data = []

        # Extract based on file type
        if extraction.extracted_tables:
            # Spreadsheet extraction
            entries_data = self.spreadsheet_extractor.extract(extraction.extracted_tables)
        else:
            # Text-based extraction (invoice/receipt)
            text = extraction.extracted_text or ""
            if "invoice" in text.lower():
                entries_data = self.invoice_extractor.extract(text)
            else:
                entries_data = self.receipt_extractor.extract(text)

        # Create entries
        entries = []
        for entry_data in entries_data:
            entry = FinancialEntry(
                tenant_id=tenant_id,
                batch_id=batch_id,
                file_id=file_id,
                source_page=entry_data.get("source_page"),
                source_row=entry_data.get("source_row"),
                original_description=entry_data.get("original_description"),
                amount=entry_data.get("amount"),
                currency=entry_data.get("currency", "USD"),
                vendor_name=entry_data.get("vendor_name"),
                invoice_number=entry_data.get("invoice_number"),
                status=EntryStatus.EXTRACTED,
            )
            db.add(entry)
            entries.append(entry)

        db.commit()
        logger.info("entries_extracted", file_id=file_id, count=len(entries))
        return entries

    def get_entries(
        self, db: Session, tenant_id: UUID, file_id: Optional[UUID] = None
    ) -> List[FinancialEntry]:
        """Get entries with optional filtering"""
        query = db.query(FinancialEntry).filter(FinancialEntry.tenant_id == tenant_id)
        if file_id:
            query = query.filter(FinancialEntry.file_id == file_id)
        return query.all()
