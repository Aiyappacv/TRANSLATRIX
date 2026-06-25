export type PlatformCompanyStatus = "active" | "trial" | "suspended" | "pending";
export type PlatformHealthStatus = "operational" | "degraded" | "outage" | "maintenance" | "not_configured" | "unknown";
export type QueueStatus = "healthy" | "delayed" | "blocked";
export type PlatformErrorSeverity = "critical" | "high" | "medium" | "low";

export interface PlatformCompany {
  id: string;
  tenantId: string;
  companyName: string;
  country: string;
  industry: string;
  plan: "Starter" | "Growth" | "Enterprise";
  status: PlatformCompanyStatus;
  users: number;
  filesProcessed: number;
  entriesProcessed: number;
  sapPostings: number;
  accountingPostings: number;
  storageUsedGb: number;
  createdAt: string;
  lastActivityAt: string;
  adminEmail: string;
  billingStatus: "current" | "trial" | "past_due";
  trialEndsAt?: string;
  mfaCoverage: number;
  ipRestrictionsEnabled: boolean;
}


export interface PlatformCompanySecurityPolicy {
  mfaRequired: boolean;
  mfaRequiredForPrivilegedRoles: boolean;
  resetMfaEnrollments?: boolean;
}

export interface PlatformKpi {
  key: string;
  label: string;
  value: number;
  unit?: "number" | "percent" | "currency" | "storage";
  delta?: string;
  tone?: "success" | "warning" | "danger" | "info" | "neutral";
}

export interface PlatformUsagePoint {
  date: string;
  files: number;
  entries: number;
  ocrPages: number;
  postings: number;
}

export interface PlatformDashboardSummary {
  kpis: PlatformKpi[];
  usageTrend: PlatformUsagePoint[];
  topCompanies: Array<{ companyId: string; companyName: string; filesProcessed: number; entriesProcessed: number; storageUsedGb: number }>;
}

export interface ProviderMonitor {
  code: string;
  name: string;
  category: "ocr" | "erp" | "accounting";
  status: PlatformHealthStatus;
  environment: string;
  uptimePercent: number | null;
  successRate: number | null;
  latencyMs: number | null;
  requests24h: number;
  incidentsOpen: number;
  lastCheckedAt: string;
  message?: string;
}

export interface SystemHealthService {
  id: string;
  name: string;
  region: string;
  status: PlatformHealthStatus;
  uptimePercent: number;
  latencyMs: number;
  cpuPercent: number;
  memoryPercent: number;
  lastDeploymentAt: string;
  message?: string;
}

export interface JobQueueMetric {
  id: string;
  name: string;
  type: "ingestion" | "ocr" | "classification" | "review" | "posting";
  status: QueueStatus;
  waiting: number;
  active: number;
  failed: number;
  completed24h: number;
  oldestJobAgeSeconds: number;
  throughputPerMinute: number;
}

export interface PlatformErrorRecord {
  id: string;
  code: string;
  title: string;
  severity: PlatformErrorSeverity;
  status: "open" | "investigating" | "resolved";
  source: string;
  companyId?: string;
  companyName?: string;
  occurrences: number;
  firstSeenAt: string;
  lastSeenAt: string;
  owner?: string;
  correlationId: string;
  message: string;
}

export interface SubscriptionPlan {
  id: string;
  name: "Starter" | "Growth" | "Enterprise";
  monthlyPrice: number;
  companies: number;
  includedFiles: number;
  includedStorageGb: number;
  includedUsers: number;
  overageRate: number;
  active: boolean;
}

export interface PlatformInvoice {
  id: string;
  companyId: string;
  companyName: string;
  billingPeriod: string;
  amount: number;
  currency: string;
  status: "paid" | "open" | "past_due";
  issuedAt: string;
  dueAt: string;
}

export interface PlatformAuditRecord {
  id: string;
  actor: string;
  action: string;
  targetType: string;
  targetName: string;
  companyName?: string;
  ipAddress: string;
  createdAt: string;
  result: "success" | "denied" | "failed";
  details: string;
}

export interface SupportTicket {
  id: string;
  companyId: string;
  companyName: string;
  subject: string;
  priority: "urgent" | "high" | "normal" | "low";
  status: "new" | "in_progress" | "waiting_customer" | "resolved";
  owner?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PlatformSettings {
  environment: "production" | "staging";
  maintenanceMode: boolean;
  tenantImpersonationEnabled: boolean;
  requireAuditReason: boolean;
  defaultTrialDays: number;
  dataRetentionDays: number;
  queueAlertThreshold: number;
  errorAlertEmail: string;
  supportEmail: string;
  statusPageUrl: string;
}

export interface PlatformRegistrationRequest {
  id: string;
  companyId: string;
  companyName: string;
  adminEmail: string;
  country: string;
  industry: string;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
  approvedAt?: string;
  approvedBy?: string;
}

export interface PlatformRegistrationApprovalResult {
  request: PlatformRegistrationRequest;
  company: PlatformCompany;
  activationPath: string;
}

export interface PlatformCompanyProvisioningInput {
  legalName: string;
  adminEmail: string;
  country: string;
  industry: string;
  plan: PlatformCompany["plan"];
  defaultCurrency: string;
  companyCode: string;
  timezone: string;
  requireMfa: boolean;
  allowAuditedSupportAccess: boolean;
}

export interface PlatformProvisioningResult {
  company: PlatformCompany;
  jobId: string;
  status: "queued" | "completed";
  createdAt: string;
}

export interface PlatformIncidentInput {
  title: string;
  severity: PlatformErrorSeverity;
  source: string;
  companyId?: string;
  companyName?: string;
  message: string;
  owner: string;
}

export interface SubscriptionPlanInput {
  name: SubscriptionPlan["name"];
  monthlyPrice: number;
  includedFiles: number;
  includedStorageGb: number;
  includedUsers: number;
  overageRate: number;
  active: boolean;
}

export interface SupportTicketInput {
  companyId: string;
  companyName: string;
  subject: string;
  priority: SupportTicket["priority"];
  owner?: string;
}
