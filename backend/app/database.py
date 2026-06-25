"""
Database Configuration and Session Management
PostgreSQL with SQLAlchemy ORM
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session
    Ensures session is properly closed after request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize all SQLAlchemy models and create their tables.

    Production deployments should use Alembic migrations; this helper is kept
    for local development and automated integration tests.
    """
    from app.modules.tenants import models as tenant_models
    from app.modules.companies import models as company_models
    from app.modules.users import models as user_models
    from app.modules.onboarding import models as onboarding_models
    from app.modules.super_admin import models as super_admin_models
    from app.modules.files import models as file_models
    from app.modules.ingestion import models as ingestion_models
    from app.modules.extraction import models as extraction_models
    from app.modules.ocr import models as ocr_models
    from app.modules.entries import models as entries_models
    from app.modules.classification import models as classification_models
    from app.modules.sap_mapping import models as sap_mapping_models
    from app.modules.accounting import models as accounting_models
    from app.modules.validation import models as validation_models
    from app.modules.review import models as review_models
    from app.modules.approvals import models as approval_models
    from app.modules.sap import models as sap_models
    from app.modules.audit import models as audit_models
    from app.modules.analytics import models as analytics_models
    from app.modules.notifications import models as notifications_models
    from app.modules.frontend_api import models as frontend_api_models
    from app.modules.ingestion import tiered_storage  # LakeRecord, ProcessingAudit, DocumentEmbedding
    from app.modules.ingestion import data_intake_models  # IntakeRegistry, IntakeEvent

    Base.metadata.create_all(bind=engine)
