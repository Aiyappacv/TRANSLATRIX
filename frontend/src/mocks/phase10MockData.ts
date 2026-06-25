import type {
  JobQueueMetric,
  PlatformAuditRecord,
  PlatformCompany,
  PlatformDashboardSummary,
  PlatformErrorRecord,
  PlatformInvoice,
  PlatformSettings,
  ProviderMonitor,
  SubscriptionPlan,
  SupportTicket,
  SystemHealthService,
} from "@/types";

export const phase10Companies: PlatformCompany[] = [];
export const phase10Dashboard: PlatformDashboardSummary = { kpis: [], usageTrend: [], topCompanies: [] };
export const phase10Providers: ProviderMonitor[] = [];
export const phase10SystemHealth: SystemHealthService[] = [];
export const phase10JobQueues: JobQueueMetric[] = [];
export const phase10Errors: PlatformErrorRecord[] = [];
export const phase10SubscriptionPlans: SubscriptionPlan[] = [];
export const phase10Invoices: PlatformInvoice[] = [];
export const phase10AuditRecords: PlatformAuditRecord[] = [];
export const phase10SupportTickets: SupportTicket[] = [];
export const phase10PlatformSettings: PlatformSettings = {
  environment: "production",
  maintenanceMode: false,
  tenantImpersonationEnabled: false,
  requireAuditReason: true,
  defaultTrialDays: 0,
  dataRetentionDays: 0,
  queueAlertThreshold: 0,
  errorAlertEmail: "",
  supportEmail: "",
  statusPageUrl: "",
};
