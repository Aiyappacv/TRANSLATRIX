from fastapi import APIRouter

from app.modules.frontend_api.analytics_routes import router as analytics_router
from app.modules.frontend_api.auth_routes import router as auth_router
from app.modules.frontend_api.company_routes import router as company_router
from app.modules.frontend_api.document_registry_routes import router as document_registry_router
from app.modules.frontend_api.document_routes import router as document_router
from app.modules.frontend_api.finance_routes import router as finance_router
from app.modules.frontend_api.ingestion_routes import router as ingestion_router
from app.modules.frontend_api.integration_routes import router as integration_router
from app.modules.frontend_api.onboarding_routes import router as onboarding_router
from app.modules.frontend_api.settings_routes import router as settings_router
from app.modules.frontend_api.super_admin_routes import router as super_admin_router
from app.modules.ingestion.data_intake_routes import router as data_intake_router

router = APIRouter()
for child in (auth_router, company_router, onboarding_router, analytics_router, ingestion_router, document_router, document_registry_router, finance_router, integration_router, settings_router, super_admin_router, data_intake_router):
    router.include_router(child)
