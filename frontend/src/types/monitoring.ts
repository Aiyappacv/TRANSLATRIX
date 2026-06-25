export type LogLevel = "info" | "success" | "warning" | "error";
export type ErrorCategory = "ocr" | "validation" | "sap_posting" | "integration";

export interface AnalyticsMetric { key: string; label: string; value: string; delta: string; tone: "success" | "warning" | "danger" | "info" | "neutral"; }
export interface AnalyticsPoint { period: string; files: number; entries: number; ocrConfidence: number; classificationConfidence: number; sapSuccess: number; sapFailure: number; approvalMinutes: number; }
export interface AnalyticsBreakdown { label: string; value: number; }
export interface AnalyticsDetail {
  metrics: AnalyticsMetric[];
  trend: AnalyticsPoint[];
  entriesByCategory: AnalyticsBreakdown[];
  validationErrors: AnalyticsBreakdown[];
  topClients: AnalyticsBreakdown[];
  failedFileTypes: AnalyticsBreakdown[];
}

export interface AuditLogRecord {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  entityType: string;
  entityId: string;
  oldValue?: unknown;
  newValue?: unknown;
  ipAddress: string;
  requestId: string;
  batchId?: string;
  entryId?: string;
  sapPostingId?: string;
  metadata: Record<string, unknown>;
}

export interface ProcessingLogRecord {
  id: string;
  timestamp: string;
  level: LogLevel;
  stage: "worker" | "batch" | "file" | "ocr" | "classification" | "validation" | "sap_posting";
  jobId: string;
  batchId?: string;
  fileId?: string;
  message: string;
  durationMs?: number;
  retryCount: number;
  requestId: string;
}

export interface ErrorCenterRecord {
  id: string;
  category: ErrorCategory;
  code: string;
  message: string;
  entityType: string;
  entityId: string;
  occurredAt: string;
  retryable: boolean;
  severity: "critical" | "high" | "medium" | "low";
  attempts: number;
  requestId: string;
  details: Record<string, unknown>;
}
