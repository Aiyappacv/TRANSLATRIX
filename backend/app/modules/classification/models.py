"""Classification Models"""
from sqlalchemy import Column, String, DateTime, Numeric, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class ClassificationMethod(enum.Enum):
    """Classification method"""
    RULE_BASED = "rule_based"
    AI_BASED = "ai_based"
    MANUAL = "manual"
    HYBRID = "hybrid"


class FinancialClassification(Base):
    """Financial entry classification results"""
    __tablename__ = "financial_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False, unique=True)

    # Classification result
    category = Column(String(100), nullable=False)  # expenses, income, assets, liabilities
    subcategory = Column(String(100), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text, nullable=True)
    classification_method = Column(SQLEnum(ClassificationMethod), nullable=False)

    # AI metadata
    model_used = Column(String(100), nullable=True)
    alternative_categories = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)  # Other possible categories with scores

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
