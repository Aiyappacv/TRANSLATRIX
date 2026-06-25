export interface AuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  entityType: "company" | "file" | "entry" | "review" | "posting" | "integration" | "mapping";
  entityId: string;
  status: "success" | "warning" | "failed" | "info";
  oldValue?: string;
  newValue?: string;
  metadata?: Record<string, unknown>;
}
