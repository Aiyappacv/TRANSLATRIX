import type { AuditEvent } from "@/types";
import { apiRequest } from "./apiClient";

export const auditApi = {
  getAuditEvents: () => apiRequest<AuditEvent[]>("/audit"),
};
