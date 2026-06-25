export const environment = {
  appName: import.meta.env.VITE_APP_NAME ?? "TRANSLATRIX PRO",
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "/api/v1/frontend",
  environmentName: import.meta.env.VITE_ENVIRONMENT ?? "local",
  maintenanceMode: import.meta.env.VITE_MAINTENANCE_MODE === "true",
  sentryDsn: import.meta.env.VITE_SENTRY_DSN ?? "",
} as const;

export const featureFlags = {
  roleDashboards: import.meta.env.VITE_FEATURE_ROLE_DASHBOARDS !== "false",
  cloudOcrFallback: import.meta.env.VITE_FEATURE_CLOUD_OCR_FALLBACK !== "false",
  sapPosting: import.meta.env.VITE_FEATURE_SAP_POSTING !== "false",
  accountingConnectors: import.meta.env.VITE_FEATURE_ACCOUNTING_CONNECTORS !== "false",
  advancedAuditDiff: import.meta.env.VITE_FEATURE_ADVANCED_AUDIT_DIFF !== "false",
} as const;
