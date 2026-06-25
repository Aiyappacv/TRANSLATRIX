"""Validation Models"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Integer, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class ValidationRuleType(enum.Enum):
    """Validation rule types"""
    REQUIRED_FIELDS = "required_fields"
    DEBIT_CREDIT_BALANCE = "debit_credit_balance"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    DUPLICATE_CHECK = "duplicate_check"
    MASTER_DATA = "master_data"


class ValidationSeverity(enum.Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRule(Base):
    """Configurable validation rules"""
    __tablename__ = "validation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Rule configuration
    rule_type = Column(SQLEnum(ValidationRuleType), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(ValidationSeverity), nullable=False, default=ValidationSeverity.ERROR)

    # Rule parameters (JSON configuration)
    parameters = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ValidationResult(Base):
    """Validation execution results"""
    __tablename__ = "validation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False, index=True)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("validation_rules.id"), nullable=False)

    # Result
    is_valid = Column(Boolean, nullable=False)
    severity = Column(SQLEnum(ValidationSeverity), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
