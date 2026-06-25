# Added and Modified Files

This list compares the final fixed product with the uploaded `TRANSLATRIX_PRO_integrated_product (1).zip`. Generated folders such as `node_modules`, `dist`, Python bytecode and test caches are excluded.

## Summary

- Added: **6** files
- Modified: **61** files
- Removed: **0** files
- Existing project files, routes and features removed: **0**

## Added files

- `backend/app/modules/frontend_api/events.py`
- `backend/app/modules/frontend_api/mfa.py`
- `backend/app/modules/frontend_api/processing.py`
- `backend/app/modules/frontend_api/security_policy.py`
- `docs/FIX_ISSUES_VALIDATION.md`
- `docs/RUN_AND_UPGRADE.md`

## Modified files

- `.env.example`
- `README.md`
- `backend/Dockerfile`
- `backend/app/modules/frontend_api/analytics_routes.py`
- `backend/app/modules/frontend_api/auth_routes.py`
- `backend/app/modules/frontend_api/company_routes.py`
- `backend/app/modules/frontend_api/defaults.py`
- `backend/app/modules/frontend_api/document_routes.py`
- `backend/app/modules/frontend_api/finance_routes.py`
- `backend/app/modules/frontend_api/ingestion_routes.py`
- `backend/app/modules/frontend_api/integration_routes.py`
- `backend/app/modules/frontend_api/security.py`
- `backend/app/modules/frontend_api/settings_routes.py`
- `backend/app/modules/frontend_api/utils.py`
- `backend/requirements-runtime.txt`
- `backend/scripts/integration_smoke_test.py`
- `docker-compose.yml`
- `docs/API_ENDPOINT_MAPPING.md`
- `docs/ENDPOINT_CORRECTIONS.md`
- `docs/FILES_CHANGED.md`
- `docs/LIMITATIONS.md`
- `docs/TEST_CREDENTIALS.md`
- `docs/TEST_REPORT.md`
- `frontend/src/app/routeConfig.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/components/files/ExtractedTablesGrid.tsx`
- `frontend/src/components/files/FileTranslationPanel.tsx`
- `frontend/src/components/files/PaddleOcrResultPanel.tsx`
- `frontend/src/components/files/ProcessingLogsPanel.tsx`
- `frontend/src/components/layout/AppSidebar.tsx`
- `frontend/src/components/layout/QuickActionsPanel.tsx`
- `frontend/src/components/ui/switch.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/batches/BatchesPage.tsx`
- `frontend/src/pages/entries/FinancialEntryDetailPage.tsx`
- `frontend/src/pages/files/FileDetailPage.tsx`
- `frontend/src/pages/files/FilesPage.tsx`
- `frontend/src/pages/ingestion/SharedLinkDetailPage.tsx`
- `frontend/src/pages/ingestion/SharedLinksPage.tsx`
- `frontend/src/pages/integrations/AccountingIntegrationsPage.tsx`
- `frontend/src/pages/integrations/IntegrationDetailPage.tsx`
- `frontend/src/pages/integrations/TallyExportPage.tsx`
- `frontend/src/pages/review/ReviewQueuePage.tsx`
- `frontend/src/pages/sap/SapIntegrationSettingsPage.tsx`
- `frontend/src/pages/settings/OCRSettingsPage.tsx`
- `frontend/src/pages/settings/SecuritySettingsPage.tsx`
- `frontend/src/pages/settings/TranslationSettingsPage.tsx`
- `frontend/src/schemas/settings.schema.ts`
- `frontend/src/services/apiClient.ts`
- `frontend/src/services/authApi.ts`
- `frontend/src/services/entryApi.ts`
- `frontend/src/services/fileApi.ts`
- `frontend/src/services/ingestionApi.ts`
- `frontend/src/services/tallyExportApi.ts`
- `frontend/src/tests/integration/production-flows.test.ts`
- `frontend/src/types/auth.ts`
- `frontend/src/types/file.ts`
- `frontend/src/types/financialEntry.ts`
- `frontend/src/utils/permissions.ts`
- `frontend/src/utils/status.ts`

## Removed files

- None

## Main change areas

- Local OCR/extraction/translation/classification/validation pipeline and review-task creation.
- File download, delete, uploader audit metadata and processing actions.
- Shared-link discovery, revalidation, synchronization and populated batch creation.
- Review, approval, correction, history and status synchronization.
- SAP eligibility safeguards, provider catalog, connection tests and posting records.
- Tally XML generation and authenticated download.
- Audit Logs, Processing Logs, Error Center and analytics aggregation.
- Auditor/Approver read-only access and finer file permissions.
- Company, OCR, translation and security settings persistence and enforcement.
- TOTP MFA login challenge and development-safe Docker project/port configuration.
