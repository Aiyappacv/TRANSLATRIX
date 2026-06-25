import type { OperationalStatus } from "@/utils/status";
import type { FileDiscoveryItem, SharedLinkProvider } from "./ingestion";

export type BatchTimelineStatus = "completed" | "processing" | "pending" | "failed" | "warning";

export interface BatchTimelineStep {
  id: string;
  label: string;
  description: string;
  status: BatchTimelineStatus;
  timestamp?: string;
  actor?: string;
}

export interface BatchError {
  id: string;
  fileName: string;
  stage: string;
  message: string;
  severity: "warning" | "error" | "critical";
  retryable: boolean;
  createdAt: string;
}

export interface BatchAuditEvent {
  id: string;
  actor: string;
  action: string;
  details: string;
  createdAt: string;
}

export interface BatchEntryPreview {
  id: string;
  document: string;
  vendor: string;
  category: "Expense" | "Income" | "Asset" | "Liability";
  amount: number;
  currency: string;
  confidence: number;
  status: OperationalStatus;
}

export interface IngestionBatch {
  id: string;
  client: string;
  sourceName: string;
  sourceType: SharedLinkProvider | string;
  provider: SharedLinkProvider | string;
  createdAt: string;
  startedAt: string;
  completedAt?: string;
  status: OperationalStatus;
  totalFiles: number;
  processedFiles: number;
  failedFiles: number;
  extractedEntries: number;
  pendingReview: number;
  postedEntries: number;
  files: number;
  entries: number;
  failed: number;
  duplicateCount: number;
  discoveredFiles: FileDiscoveryItem[];
  entryPreviews: BatchEntryPreview[];
  timeline: BatchTimelineStep[];
  errors: BatchError[];
  audit: BatchAuditEvent[];
}
