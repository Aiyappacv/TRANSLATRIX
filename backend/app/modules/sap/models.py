"""
SAP Integration Models
SAP S/4HANA configuration, mappings, and posting
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class SAPStatus(enum.Enum):
    """SAP posting status"""
    PENDING = "pending"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


class SAPConnectionConfig(Base):
    """SAP connection configuration"""
    __tablename__ = "sap_connection_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)

    base_url = Column(String(255), nullable=False)
    client = Column(String(10), nullable=False)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(Text, nullable=False)  # Encrypted
    environment = Column(String(20), nullable=False, default="sandbox")  # sandbox, production

    is_active = Column(Boolean, nullable=False, default=True)
    last_tested_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SAPTCodeMapping(Base):
    """SAP T-Code and process mappings"""
    __tablename__ = "sap_tcode_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Classification matching
    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=True)
    keywords = Column(JSON, nullable=True)

    # SAP mapping
    tcode = Column(String(20), nullable=False)  # FB60, FB50, etc.
    process_name = Column(String(255), nullable=False)
    sap_api = Column(String(255), nullable=False)  # API endpoint
    document_type = Column(String(50), nullable=True)

    # Requirements
    requires_vendor = Column(Boolean, nullable=False, default=False)
    requires_customer = Column(Boolean, nullable=False, default=False)
    requires_asset = Column(Boolean, nullable=False, default=False)
    requires_approval = Column(Boolean, nullable=False, default=True)

    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GLAccountMapping(Base):
    """GL account mappings"""
    __tablename__ = "gl_account_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=True)
    gl_account = Column(String(20), nullable=False)
    cost_center = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SAPPostingPayload(Base):
    """SAP posting request payloads"""
    __tablename__ = "sap_posting_payloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False)

    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SAPPostingResult(Base):
    """SAP posting results"""
    __tablename__ = "sap_posting_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False)
    payload_id = Column(UUID(as_uuid=True), ForeignKey("sap_posting_payloads.id"), nullable=False)

    status = Column(SQLEnum(SAPStatus), nullable=False, default=SAPStatus.PENDING)
    sap_document_number = Column(String(100), nullable=True, index=True)
    fiscal_year = Column(String(10), nullable=True)
    company_code = Column(String(20), nullable=True)

    sap_response = Column(JSON, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    posted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
