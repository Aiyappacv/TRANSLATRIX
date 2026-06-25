export type IntegrationProviderType = "erp" | "accounting" | "export" | "api" | "hris" | "itsm" | "storage" | "ocr";
export type IntegrationStatus = "connected" | "available" | "degraded" | "disabled" | "syncing" | "error";
export type IntegrationEnvironment = "sandbox" | "development" | "uat" | "production" | "local";
export type IntegrationAuthType = "oauth2" | "client_credentials" | "api_key" | "basic" | "certificate" | "sftp_key" | "none";

export interface IntegrationCapabilities {
  connectionTest: boolean;
  fieldMapping: boolean;
  financialMapping: boolean;
  masterDataSync: boolean;
  workerSync: boolean;
  ticketSync: boolean;
  tallyExport: boolean;
}

export interface IntegrationConnectionField {
  key: string;
  label: string;
  type: "text" | "password" | "url" | "number" | "select" | "textarea";
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  options?: Array<{ label: string; value: string }>;
}

export interface IntegrationProvider {
  code: string;
  name: string;
  shortName?: string;
  logoText?: string;
  type: IntegrationProviderType;
  supportsOAuth: boolean;
  supportsSandbox: boolean;
  status: IntegrationStatus;
  description: string;
  environment?: IntegrationEnvironment;
  lastTestedAt?: string;
  lastSyncAt?: string;
  supportedActions?: string[];
  authTypes?: IntegrationAuthType[];
  connectionFields?: IntegrationConnectionField[];
  documentationLabel?: string;
  version?: string;
  capabilities?: Partial<IntegrationCapabilities>;
  syncActionLabel?: string;
}

export interface IntegrationConnectionSettings {
  providerCode: string;
  displayName: string;
  environment: IntegrationEnvironment;
  authType: IntegrationAuthType;
  baseUrl?: string;
  companyCode?: string;
  tenantId?: string;
  clientId?: string;
  clientSecret?: string;
  apiKey?: string;
  webhookUrl?: string;
  customValues: Record<string, string>;
  enabled: boolean;
  autoSyncEnabled: boolean;
  syncFrequency: "manual" | "hourly" | "daily" | "weekly";
}

export interface IntegrationMappingRow {
  id: string;
  sourceField: string;
  targetField: string;
  transform?: string;
  defaultValue?: string;
  required: boolean;
  active: boolean;
}

export interface CategoryMappingRow {
  id: string;
  sourceCategory: string;
  sourceSubcategory?: string;
  targetType: string;
  targetValue: string;
  active: boolean;
}

export interface AccountMappingRow {
  id: string;
  sourceAccount: string;
  sourceLabel: string;
  targetAccount: string;
  targetLabel: string;
  companyCode?: string;
  active: boolean;
}

export interface TaxMappingRow {
  id: string;
  sourceTaxCode: string;
  sourceRate: number;
  targetTaxCode: string;
  targetRate: number;
  jurisdiction?: string;
  active: boolean;
}

export interface ConnectorLog {
  id: string;
  timestamp: string;
  level: "info" | "success" | "warning" | "error";
  operation: string;
  message: string;
  correlationId: string;
  durationMs?: number;
}

export interface IntegrationSummaryMetric {
  key: string;
  label: string;
  value: string | number;
}

export interface IntegrationDetail {
  provider: IntegrationProvider;
  settings: IntegrationConnectionSettings;
  fieldMappings: IntegrationMappingRow[];
  categoryMappings: CategoryMappingRow[];
  accountMappings: AccountMappingRow[];
  taxMappings: TaxMappingRow[];
  logs: ConnectorLog[];
  masterData: {
    vendors: number;
    customers: number;
    accounts: number;
    taxCodes: number;
    lastSyncedAt?: string;
  };
  summaryMetrics?: IntegrationSummaryMetric[];
}

export interface IntegrationTestResult {
  providerCode: string;
  status: "success" | "failed";
  latencyMs: number;
  checkedAt: string;
  message: string;
}

export interface MasterDataSyncResult {
  providerCode: string;
  status: "completed" | "failed";
  syncedAt: string;
  counts: IntegrationDetail["masterData"];
  message: string;
}

export interface CustomConnectorInput {
  name: string;
  code: string;
  type: IntegrationProviderType;
  description: string;
  baseUrl: string;
  authType: IntegrationAuthType;
  environment: IntegrationEnvironment;
}
