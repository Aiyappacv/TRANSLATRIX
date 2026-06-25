from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ROLE_PERMISSIONS = {
    "spectra_super_admin": [
        "platform:manage", "companies:manage", "platform:dashboard:read", "platform:companies:manage",
        "platform:billing:manage", "platform:usage:read", "platform:integrations:monitor", "platform:health:read",
        "platform:queues:manage", "platform:errors:manage", "platform:audit:read", "platform:support:manage",
        "platform:settings:manage", "platform:tenant:view", "dashboard:read", "onboarding:manage", "users:manage",
        "ingestion:manage", "files:read", "files:upload", "files:process", "files:manage", "entries:read", "entries:manage", "review:read", "review:edit",
        "review:assign", "review:approve", "review:request_changes", "review:second_approve", "review:export",
        "posting:read", "posting:execute", "posting:retry", "posting:download", "integrations:read",
        "integrations:manage", "integrations:test", "integrations:sync", "audit:read", "analytics:read", "settings:manage",
    ],
    "company_owner": [],
    "company_admin": [],
    "finance_manager": ["dashboard:read", "ingestion:manage", "files:read", "files:upload", "files:process", "files:manage", "entries:read", "entries:manage", "review:read", "review:edit", "review:assign", "review:approve", "review:request_changes", "review:second_approve", "review:export", "analytics:read", "audit:read", "posting:read", "posting:download"],
    "finance_user": ["dashboard:read", "ingestion:manage", "files:read", "files:upload", "files:process", "entries:read", "entries:manage", "review:read"],
    "reviewer": ["dashboard:read", "files:read", "files:process", "entries:read", "entries:manage", "review:read", "review:edit", "review:request_changes", "review:export"],
    "approver": ["dashboard:read", "files:read", "entries:read", "review:read", "review:edit", "review:approve", "review:request_changes", "review:second_approve", "review:export", "audit:read"],
    "sap_poster": ["dashboard:read", "files:read", "review:read", "posting:read", "posting:execute", "posting:retry", "posting:download", "integrations:read", "integrations:test", "audit:read"],
    "integration_manager": ["dashboard:read", "integrations:read", "integrations:manage", "integrations:test", "integrations:sync", "posting:read", "posting:download", "ingestion:manage", "settings:manage", "audit:read"],
    "auditor": ["dashboard:read", "review:read", "review:export", "audit:read", "analytics:read", "files:read", "entries:read", "posting:read", "posting:download"],
    "read_only": ["dashboard:read", "files:read", "entries:read", "review:read", "posting:read", "integrations:read"],
}
ROLE_PERMISSIONS["company_owner"] = [p for p in ROLE_PERMISSIONS["spectra_super_admin"] if not p.startswith("platform:") and p != "companies:manage"]
ROLE_PERMISSIONS["company_admin"] = list(ROLE_PERMISSIONS["company_owner"])

BACKEND_ROLE_TO_FRONTEND = {
    "super_admin": "spectra_super_admin",
    "spectra_super_admin": "spectra_super_admin",
    "company_owner": "company_owner",
    "company_admin": "company_admin",
    "finance_manager": "finance_manager",
    "company_finance_manager": "finance_manager",
    "finance_user": "finance_user",
    "accountant": "finance_user",
    "reviewer": "reviewer",
    "company_reviewer": "reviewer",
    "approver": "approver",
    "company_approver": "approver",
    "sap_poster": "sap_poster",
    "integration_manager": "integration_manager",
    "auditor": "auditor",
    "viewer": "read_only",
    "company_viewer": "read_only",
    "read_only": "read_only",
}

COMPANY_SETTINGS = {
    "legalName": "Company", "tradingName": "Company", "country": "India", "industry": "Financial Services", "registrationNumber": "REG-001", "taxId": "TAX-001",
    "defaultCurrency": "INR", "defaultLanguage": "en", "timezone": "Asia/Kolkata", "defaultCompanyCode": "1000",
    "fiscalYearVariant": "K4", "financeContact": "finance@example.com", "website": "https://example.com", "phone": "0000000000",
}
APPROVAL_RULES = {
    "approvalRequiredAbove": 0, "secondApprovalAbove": 0, "lowConfidenceRequiresReview": True,
    "confidenceThreshold": 0, "sapFailedRequiresAdminReview": True, "categoryBasedApproval": False, "categoryRules": [],
}
OCR_SETTINGS = {
    "primaryEngine": "Mistral OCR", "fallbackEngine": "PaddleOCR", "cloudFallbackEnabled": False,
    "confidenceThreshold": 80, "tableExtractionEnabled": True, "layoutAnalysisEnabled": True,
    "handwritingEnabled": False, "maxPagesPerFile": 500,
}
SECURITY_SETTINGS = {
    "mfaRequired": False, "mfaRequiredForPrivilegedRoles": False, "passwordMinimumLength": 12,
    "passwordRequireUppercase": True, "passwordRequireLowercase": True, "passwordRequireNumber": True,
    "passwordRequireSymbol": True, "passwordExpiryDays": 0, "sessionTimeoutMinutes": 30,
    "allowedIpRanges": "", "ssoEnabled": False, "ssoProvider": "Not configured", "auditRetentionDays": 365,
}
SAP_SETTINGS = {
    "id": "sap-primary", "systemName": "", "environment": "sandbox", "baseUrl": "", "authType": "oauth2_client_credentials",
    "clientId": "", "companyCode": "", "apiSelection": ["journal_entry"], "requestTimeoutSeconds": 60, "retryLimit": 3,
    "idempotencyEnabled": True, "certificateValidationEnabled": True, "status": "not_configured", "updatedAt": now_iso(),
}
PLATFORM_SETTINGS = {
    "environment": "staging", "maintenanceMode": False, "tenantImpersonationEnabled": False,
    "requireAuditReason": True, "defaultTrialDays": 14, "dataRetentionDays": 365,
    "queueAlertThreshold": 100, "errorAlertEmail": "", "supportEmail": "", "statusPageUrl": "",
}
SUBSCRIPTION_PLANS = [
    {"id": "starter", "name": "Starter", "monthlyPrice": 0, "companies": 0, "includedFiles": 1000, "includedStorageGb": 10, "includedUsers": 5, "overageRate": 0, "active": True},
    {"id": "growth", "name": "Growth", "monthlyPrice": 0, "companies": 0, "includedFiles": 10000, "includedStorageGb": 100, "includedUsers": 25, "overageRate": 0, "active": True},
    {"id": "enterprise", "name": "Enterprise", "monthlyPrice": 0, "companies": 0, "includedFiles": 100000, "includedStorageGb": 1000, "includedUsers": 250, "overageRate": 0, "active": True},
]

PROVIDERS = [
    {"code": "sap_s4hana", "name": "SAP S/4HANA", "shortName": "SAP", "logoText": "SAP", "type": "erp", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "SAP S/4HANA journal entry, supplier invoice, customer invoice, and posting integration.", "authTypes": ["client_credentials", "basic", "certificate"], "supportedActions": ["Configure", "Test connection", "Post approved entries", "Download responses"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True, "masterDataSync": True}},
    {"code": "quickbooks", "name": "QuickBooks Online", "shortName": "QuickBooks", "logoText": "QB", "type": "accounting", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "Accounting connector for invoices, journals, vendors, customers, and accounts.", "authTypes": ["oauth2"], "supportedActions": ["Test connection", "Field mapping", "Master data sync"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True, "masterDataSync": True}},
    {"code": "xero", "name": "Xero", "logoText": "XE", "type": "accounting", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "Accounting connector for Xero organizations.", "authTypes": ["oauth2"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True, "masterDataSync": True}},
    {"code": "zoho_books", "name": "Zoho Books", "logoText": "ZB", "type": "accounting", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "Zoho Books accounting connector.", "authTypes": ["oauth2"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True, "masterDataSync": True}},
    {"code": "netsuite", "name": "Oracle NetSuite", "logoText": "NS", "type": "erp", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "ERP connector for NetSuite financials.", "authTypes": ["oauth2", "client_credentials"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True, "masterDataSync": True}},
    {"code": "workday", "name": "Workday", "logoText": "WD", "type": "hris", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "Workday worker, organization, and cost-center synchronization.", "authTypes": ["oauth2", "client_credentials"], "capabilities": {"connectionTest": True, "fieldMapping": True, "masterDataSync": True, "workerSync": True}, "syncActionLabel": "Sync Workday data"},
    {"code": "servicenow", "name": "ServiceNow", "logoText": "SN", "type": "itsm", "supportsOAuth": True, "supportsSandbox": True, "status": "available", "description": "ServiceNow incident and approval workflow connector.", "authTypes": ["oauth2", "basic"], "capabilities": {"connectionTest": True, "fieldMapping": True, "ticketSync": True}},
    {"code": "webhook_api", "name": "Webhook / API Connector", "logoText": "API", "type": "api", "supportsOAuth": False, "supportsSandbox": True, "status": "available", "description": "Configurable outbound REST API and webhook connector.", "authTypes": ["api_key", "basic", "none"], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True}},
    {"code": "tallyprime", "name": "TallyPrime", "logoText": "TP", "type": "export", "supportsOAuth": False, "supportsSandbox": False, "status": "available", "description": "TallyPrime XML/JSON/CSV export connector.", "authTypes": ["none"], "capabilities": {"connectionTest": False, "fieldMapping": True, "financialMapping": True, "tallyExport": True}},
]


def provider_detail(provider: dict) -> dict:
    return {
        "provider": provider,
        "settings": {"providerCode": provider["code"], "displayName": provider["name"], "environment": "sandbox", "authType": (provider.get("authTypes") or ["none"])[0], "baseUrl": "", "customValues": {}, "enabled": False, "autoSyncEnabled": False, "syncFrequency": "manual"},
        "fieldMappings": [], "categoryMappings": [], "accountMappings": [], "taxMappings": [], "logs": [],
        "masterData": {"vendors": 0, "customers": 0, "accounts": 0, "taxCodes": 0},
        "summaryMetrics": [{"key": "status", "label": "Configuration", "value": "Not configured"}],
    }


def role_dashboard(role: str) -> dict:
    title = role.replace("_", " ").title()
    return {
        "role": role, "title": f"{title} Dashboard", "subtitle": "Live company workflow overview", "focus": "No operational data has been created yet.",
        "readOnly": role in {"auditor", "read_only"},
        "kpis": [
            {"key": "files", "label": "Files", "value": "0", "delta": "No activity", "tone": "neutral", "icon": "Files"},
            {"key": "entries", "label": "Entries", "value": "0", "delta": "No activity", "tone": "neutral", "icon": "TableProperties"},
            {"key": "reviews", "label": "Pending reviews", "value": "0", "delta": "Queue clear", "tone": "success", "icon": "ClipboardCheck"},
            {"key": "postings", "label": "Posted", "value": "0", "delta": "No activity", "tone": "neutral", "icon": "Send"},
        ],
        "tasks": [], "processing": [], "sapPosting": [], "validation": [], "integrations": [], "categoryBreakdown": [],
        "recentFiles": [], "recentEntries": [], "auditActivity": [],
        "quickActions": [
            {"label": "Upload file", "href": "/app/files", "permission": "files:upload"},
            {"label": "Create shared link", "href": "/app/ingestion/shared-links/new", "permission": "ingestion:manage"},
        ],
    }
