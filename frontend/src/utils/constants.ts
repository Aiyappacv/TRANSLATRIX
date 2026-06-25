export const APP_NAME = import.meta.env.VITE_APP_NAME ?? "TRANSLATRIX PRO";
export const DEFAULT_TENANT_ID = import.meta.env.VITE_DEFAULT_TENANT_ID ?? "";
export const USE_MOCKS = false;

export const financialCategories = ["Expenses", "Income", "Assets", "Liabilities"] as const;
export const providerCodes = ["sap_s4hana", "quickbooks", "xero", "zoho", "netsuite", "sage", "tally", "dynamics", "odoo", "csv"] as const;
