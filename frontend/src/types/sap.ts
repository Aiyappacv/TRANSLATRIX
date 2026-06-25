import type { AccountingLine, FinancialEntry } from "./financialEntry";
import type { AccountingEntryPayload } from "./accounting";
import type { AuditEvent } from "./audit";

export interface SapMappingRule {
  id: string;
  category: string;
  subcategory: string;
  keywords: string[];
  tCode: string;
  apiProcess: string;
  sapApi?: string;
  documentType: string;
  glAccount: string;
  taxCode?: string;
  costCenter?: string;
  requiresVendor: boolean;
  requiresCustomer: boolean;
  requiresAsset?: boolean;
  requiresCostCenter?: boolean;
  approvalRequired: boolean;
  priority: number;
  active: boolean;
}

export type SapPostingStatus =
  | "ready"
  | "queued"
  | "posting"
  | "posted"
  | "failed"
  | "reversed";
export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "second_approval_required";

export interface PostingResult {
  id: string;
  entryId: string;
  providerCode: string;
  externalDocumentNumber?: string;
  fiscalYear?: string;
  companyCode?: string;
  status: "queued" | "posted" | "failed" | "reversed";
  errorCode?: string;
  errorMessage?: string;
  postedAt?: string;
}

export interface SapPostingTimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  status: "completed" | "current" | "failed" | "pending";
  actor: string;
}

export interface SapResponsePayload {
  success: boolean;
  httpStatus: number;
  requestId: string;
  sapDocumentNumber?: string;
  fiscalYear?: string;
  companyCode?: string;
  message: string;
  error?: {
    code: string;
    target?: string;
    details: string[];
  };
}

export interface SapPostingRecord {
  id: string;
  entryId: string;
  category: string;
  sapTCode: string;
  sapProcess: string;
  companyCode: string;
  amount: number;
  currency: string;
  approvalStatus: ApprovalStatus;
  sapStatus: SapPostingStatus;
  sapDocumentNumber?: string;
  fiscalYear?: string;
  attempts: number;
  lastAttemptAt?: string;
  approvedAt?: string;
  approvedBy?: string;
  payload: AccountingEntryPayload;
  response?: SapResponsePayload;
  errorCode?: string;
  errorMessage?: string;
  accountingLines: AccountingLine[];
  sourceEntry?: FinancialEntry;
  timeline: SapPostingTimelineEvent[];
  auditEvents: AuditEvent[];
}

export type SapEnvironment =
  | "sandbox"
  | "development"
  | "quality"
  | "uat"
  | "production";
export type SapAuthType =
  | "oauth2_client_credentials"
  | "basic"
  | "certificate"
  | "destination_service";
export type SapApiSelection =
  | "journal_entry"
  | "supplier_invoice"
  | "customer_invoice"
  | "asset_accounting"
  | "bank_statement";

export interface SapIntegrationSettings {
  id: string;
  systemName: string;
  environment: SapEnvironment;
  baseUrl: string;
  authType: SapAuthType;
  clientId: string;
  clientSecret?: string;
  companyCode: string;
  apiSelection: SapApiSelection[];
  requestTimeoutSeconds: number;
  retryLimit: number;
  idempotencyEnabled: boolean;
  certificateValidationEnabled: boolean;
  status: "connected" | "degraded" | "not_configured";
  lastTestedAt?: string;
  lastTestLatencyMs?: number;
  updatedAt: string;
}

export interface SapPostingConfigurationStatus {
  status: "connected" | "degraded" | "failed" | "not_configured";
  canPost: boolean;
  message: string;
  lastTestedAt?: string;
}

export interface SapConnectionTestResult {
  status: "success" | "failed";
  latencyMs: number;
  checkedAt: string;
  systemVersion?: string;
  message: string;
}
