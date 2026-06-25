"""Accounting Models"""
from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class AccountingEntryType(enum.Enum):
    """Accounting entry type"""
    DEBIT = "debit"
    CREDIT = "credit"


class AccountingEntry(Base):
    """Accounting entries (debit/credit)"""
    __tablename__ = "accounting_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    financial_entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False, index=True)

    # Entry details
    entry_type = Column(SQLEnum(AccountingEntryType), nullable=False)
    gl_account = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")

    # SAP integration
    tcode = Column(String(20), nullable=True)
    cost_center = Column(String(50), nullable=True)
    profit_center = Column(String(50), nullable=True)

    # Description
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
