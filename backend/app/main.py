"""
TRANSLATRIX PRO - Main FastAPI Application
Enterprise SaaS AI-Finance Automation Platform
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIDMiddleware,
    TenantContextMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware
)
from app.core.response import success_response

# Configure logging before creating app
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Startup and shutdown hooks
    """
    # Startup
    logger.info("starting_application", app_name=settings.APP_NAME, env=settings.APP_ENV)

    # Validate Gemini API key presence and warn if missing — extraction will
    # still operate using deterministic fallbacks (Mistral OCR) but Gemini is
    # the preferred high-accuracy model.
    if not settings.GEMINI_API_KEY:
        logger.warning("gemini_api_key_missing", message="GEMINI_API_KEY is not set — Gemini extraction disabled. Set GEMINI_API_KEY in .env to enable.")
    else:
        logger.info("gemini_api_key_present")

    if settings.RUN_DB_BOOTSTRAP:
        from app.database import init_db
        init_db()
        logger.info("database_tables_created")

    if settings.SEED_DEVELOPMENT and not settings.is_production():
        from scripts.seed_development import main as seed_development
        seed_development()

    from app.modules.frontend_api.pdf_renderer import init_renderer, available_renderer
    renderer = init_renderer()
    if renderer:
        logger.info("preview_renderer_available", renderer=renderer)
    else:
        logger.warning("preview_renderer_unavailable", reason="No PDF renderer dependency found")

    from app.modules.ingestion.data_intake_service import _get_embedding_model
    if _get_embedding_model() is not None:
        logger.info("embedding_model_preloaded")

    from app.modules.ingestion.worker import configure_pool_concurrency, get_worker
    configure_pool_concurrency("metadata", settings.METADATA_WORKER_CONCURRENCY)
    configure_pool_concurrency("extraction", settings.EXTRACTION_WORKER_CONCURRENCY)
    metadata_worker = await get_worker("metadata")
    extraction_worker = await get_worker("extraction")
    logger.info(
        "background_worker_started metadata_concurrency=%d extraction_concurrency=%d",
        metadata_worker.max_concurrency, extraction_worker.max_concurrency,
    )

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("shutting_down_application")
    from app.modules.ingestion.worker import shutdown_worker
    await shutdown_worker()
    logger.info("background_worker_stopped")
    logger.info("application_stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise AI-Finance Automation Platform - Production Backend",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Custom Middleware (order matters - last added is first executed)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RequestIDMiddleware)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return success_response(
        data={
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
            "docs_url": "/docs" if settings.DEBUG else None,
        },
        message="TRANSLATRIX PRO API"
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    Returns application health status
    """
    return success_response(
        data={
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
        },
        message="Service is healthy"
    )


# Readiness probe for Kubernetes
@app.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes
    Verify all dependencies are ready
    """
    from app.core.health import check_all_dependencies, is_system_ready

    dependencies = check_all_dependencies()
    is_ready = is_system_ready()

    if is_ready:
        return success_response(
            data={
                "ready": True,
                "dependencies": dependencies
            },
            message="Service is ready"
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "dependencies": dependencies
            }
        )


# Frontend compatibility API (exact contracts used by the React application)
from app.modules.frontend_api.routes import router as frontend_api_router

# Register API routers - Phase 2: Auth, Tenant, Company & User Management
from app.modules.auth.routes import router as auth_router
from app.modules.companies.routes import router as companies_router
from app.modules.users.routes import router as users_router
from app.modules.onboarding.routes import router as onboarding_router

# Phase 3: Super Admin Module
from app.modules.super_admin.routes import router as super_admin_router

# Phase 4: Shared Link Ingestion
from app.modules.ingestion.routes import router as ingestion_router

# Phase 4a: Data Intake (Enterprise Data Ingestion Module)
from app.modules.ingestion.data_intake_routes import router as data_intake_router

# Phase 5: File Service & Storage
from app.modules.files.routes import router as files_router

# Phase 6: Extraction & OCR
from app.modules.extraction.routes import router as extraction_router
from app.modules.ocr.routes import router as ocr_router

# Phase 8: Entries & Classification
from app.modules.entries.routes import router as entries_router
from app.modules.classification.routes import router as classification_router

# Phase 9: SAP Mapping & Accounting
from app.modules.sap_mapping.routes import router as sap_mapping_router
from app.modules.accounting.routes import router as accounting_router

# Phase 10: Validation
from app.modules.validation.routes import router as validation_router

# Phase 11: Review & Approvals
from app.modules.review.routes import router as review_router
from app.modules.approvals.routes import router as approvals_router

# Phase 12: SAP Integration
from app.modules.sap.routes import router as sap_router

# Phase 13: Accounting Integrations
from app.modules.accounting_integrations.routes import router as accounting_integrations_router

# Phase 14: Audit, Analytics & Notifications
from app.modules.audit.routes import router as audit_router
from app.modules.analytics.routes import router as analytics_router
from app.modules.notifications.routes import router as notifications_router

# Phase 15: Monitoring
from app.modules.monitoring.routes import router as monitoring_router

# Frontend compatibility API. Existing backend endpoints remain unchanged.
app.include_router(frontend_api_router, prefix=f"{settings.API_V1_PREFIX}/frontend", tags=["Frontend Integration API"])

# Authentication & Registration
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])

# Company Management
app.include_router(companies_router, prefix=f"{settings.API_V1_PREFIX}/companies", tags=["Companies"])

# User Management
app.include_router(users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])

# Onboarding Workflow
app.include_router(onboarding_router, prefix=f"{settings.API_V1_PREFIX}/onboarding", tags=["Onboarding"])

# Super Admin (Phase 3)
app.include_router(super_admin_router, prefix=f"{settings.API_V1_PREFIX}/super-admin", tags=["Super Admin"])

# File Management (Phase 5)
app.include_router(files_router, prefix=f"{settings.API_V1_PREFIX}/files", tags=["Files"])

# Extraction & OCR (Phase 6)
app.include_router(extraction_router, prefix=f"{settings.API_V1_PREFIX}/files", tags=["Extraction"])
app.include_router(ocr_router, prefix=f"{settings.API_V1_PREFIX}/files", tags=["OCR"])

# Shared Link Ingestion (Phase 4)
app.include_router(ingestion_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Ingestion"])

# Data Intake / Enterprise Ingestion (Phase 4a)
app.include_router(data_intake_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Data Intake"])

# Entries & Classification (Phase 8)
app.include_router(entries_router, prefix=f"{settings.API_V1_PREFIX}/entries", tags=["Entries"])
app.include_router(classification_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Classification"])

# SAP Mapping & Accounting (Phase 9)
app.include_router(sap_mapping_router, prefix=f"{settings.API_V1_PREFIX}/sap-mapping", tags=["SAP Mapping"])
app.include_router(accounting_router, prefix=f"{settings.API_V1_PREFIX}/accounting", tags=["Accounting"])

# Validation (Phase 10)
app.include_router(validation_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Validation"])

# Review & Approvals (Phase 11)
app.include_router(review_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Review"])
app.include_router(approvals_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Approvals"])

# SAP Integration (Phase 12)
app.include_router(sap_router, prefix=f"{settings.API_V1_PREFIX}/sap", tags=["SAP Integration"])

# Accounting Integrations (Phase 13)
app.include_router(accounting_integrations_router, prefix=f"{settings.API_V1_PREFIX}/accounting-integrations", tags=["Accounting Integrations"])

# Audit, Analytics & Notifications (Phase 14)
app.include_router(audit_router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["Audit"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"])
app.include_router(notifications_router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["Notifications"])

# Monitoring (Phase 15)
app.include_router(monitoring_router, prefix=f"{settings.API_V1_PREFIX}/monitoring", tags=["Monitoring"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
