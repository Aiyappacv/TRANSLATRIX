import type { AnalyticsDetail, AuditLogRecord, ErrorCenterRecord, ProcessingLogRecord } from "@/types";
import { apiRequest } from "./apiClient";

export const monitoringApi = {
  getAnalytics: () => apiRequest<AnalyticsDetail>("/analytics/enterprise"),
  getAuditLogs: () => apiRequest<AuditLogRecord[]>("/audit/logs"),
  getProcessingLogs: () => apiRequest<ProcessingLogRecord[]>("/monitoring/processing-logs"),
  getErrors: () => apiRequest<ErrorCenterRecord[]>("/monitoring/errors"),
  retryError: (id: string) => apiRequest<{ id: string; status: "queued" }>(`/monitoring/errors/${id}/retry`, { method: "POST" }),
};
