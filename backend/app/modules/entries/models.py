"""
Financial Entry Models
Financial entries, classifications, and processing pipeline
"""
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, ForeignKey, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class FinancialCategory(enum.Enum):
    """Financial entry categories"""
    EXPENSES = "expenses"
    INCOME = "income"
    ASSETS = "assets"
    LIABILITIES = "liabilities"


class EntryStatus(enum.Enum):
    """Entry processing status"""
    EXTRACTED = "extracted"
    CLASSIFIED = "classified"
    MAPPED = "mapped"
    ACCOUNTING_GENERATED = "accounting_generated"
    VALIDATION_FAILED = "validation_failed"
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SAP_READY = "sap_ready"
    SAP_POSTING = "sap_posting"
    SAP_POSTED = "sap_posted"
    SAP_FAILED = "sap_failed"


class FinancialEntry(Base):
    """Financial entry extracted from documents"""
    __tablename__ = "financial_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("ingestion_batches.id"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("ingested_files.id"), nullable=False)

    # Source location
    source_page = Column(Integer, nullable=True)
    source_row = Column(Integer, nullable=True)

    # Content
    original_description = Column(Text, nullable=True)
    translated_description = Column(Text, nullable=True)

    # Financial data
    entry_date = Column(Date, nullable=True)
    amount = Column(Numeric(18, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    tax_amount = Column(Numeric(18, 2), nullable=True)

    # Parties
    vendor_name = Column(String(255), nullable=True)
    vendor_code = Column(String(100), nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_code = Column(String(100), nullable=True)

    # References
    reference_number = Column(String(100), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    po_number = Column(String(100), nullable=True)

    # Classification
    category = Column(SQLEnum(FinancialCategory), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    classification_confidence = Column(Numeric(5, 2), nullable=True)

    # Processing status
    status = Column(SQLEnum(EntryStatus), nullable=False, default=EntryStatus.EXTRACTED, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
