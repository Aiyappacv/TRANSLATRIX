import type {
  LinkValidationResult,
  SharedLinkSource,
  PreprocessingResult,
  DedupResult,
  PreviewInfo,
  ExtractionJobResponse,
  LakeTierRecord,
  ProcessingAuditEntry,
  ExportRequest,
  ExportResponse,
  IntakeRegistryListResponse,
  IntakeRegistryEntry,
  UploadResponse,
  CheckDuplicateResponse,
  IntakePreviewResponse,
  ExtractNavigationResponse,
  DeleteResponse,
  BulkDeleteResponse,
  IntakeEventResponse,
  BatchProgressResponse,
  BatchUploadResponse,
  RetryExtractionResponse,
} from "@/types";
import type { SharedLinkInput } from "@/schemas/ingestion.schema";
import { apiRequest } from "./apiClient";

export const ingestionApi = {
  // Shared Links
  getSharedLinks: () => apiRequest<SharedLinkSource[]>("/shared-links"),
  getSharedLink: (id: string) => apiRequest<SharedLinkSource>(`/shared-links/${id}`),
  validateSharedLink: (payload: SharedLinkInput) =>
    apiRequest<LinkValidationResult>("/shared-links/validate", { method: "POST", body: JSON.stringify(payload) }),
  syncAll: () =>
    apiRequest<{ status: string; syncedAt: string }>("/shared-links/sync-all", { method: "POST" }),
  revalidateSharedLink: (id: string) =>
    apiRequest<SharedLinkSource>(`/shared-links/${id}/validate`, { method: "POST" }),
  syncSharedLink: (id: string) =>
    apiRequest<SharedLinkSource>(`/shared-links/${id}/sync`, { method: "POST" }),
  createBatchFromSource: (sourceId: string) =>
    apiRequest<{ batchId: string; status: string }>(`/shared-links/${sourceId}/create-batch`, { method: "POST" }),
  createSharedLink: (payload: SharedLinkInput) =>
    apiRequest<SharedLinkSource>("/shared-links", { method: "POST", body: JSON.stringify(payload) }),

  // Preprocessing
  preprocessFile: (fileId: string) =>
    apiRequest<PreprocessingResult>(`/files/${fileId}/preprocess`, { method: "POST" }),

  // Deduplication
  deduplicateFile: (fileId: string) =>
    apiRequest<DedupResult>(`/files/${fileId}/deduplicate`, { method: "POST" }),

  // Preview
  getFilePreview: (fileId: string, page = 1) =>
    apiRequest<PreviewInfo>(`/files/${fileId}/preview-pages?page=${page}`),

  // Extraction
  extractFields: (fileId: string) =>
    apiRequest<ExtractionJobResponse>(`/files/${fileId}/extract`, { method: "POST" }),

  // Export
  exportAsJson: (payload: ExportRequest) =>
    apiRequest<ExportResponse>("/export", { method: "POST", body: JSON.stringify(payload) }),

  // Tier / Audit
  getFileTiers: (fileId: string) =>
    apiRequest<LakeTierRecord[]>(`/files/${fileId}/tiers`),
  getFileAuditLog: (fileId: string) =>
    apiRequest<ProcessingAuditEntry[]>(`/files/${fileId}/audit`),

  // ── Data Intake / Enterprise Ingestion Module ────────────────

  /** Upload a single file: validated, streamed to storage, and registered
   * synchronously (fast — no checksum/duplicate/page-count work happens
   * here). Returns the registry entry immediately; background metadata
   * processing starts right after. */
  uploadFile: async (file: File, sourceChannel = "portal") => {
    const data = new FormData();
    data.append("file", file);
    data.append("source_channel", sourceChannel);
    return apiRequest<UploadResponse>("/data-ingestion/upload", { method: "POST", body: data });
  },

  /** Upload multiple files: streamed to storage concurrently and registered
   * in a single transaction, returning as soon as registration completes —
   * not after every file's metadata has been computed. */
  uploadBatch: async (files: File[], sourceChannel = "portal") => {
    const data = new FormData();
    files.forEach((f) => data.append("files", f));
    data.append("source_channel", sourceChannel);
    return apiRequest<BatchUploadResponse>("/data-ingestion/upload/batch", {
      method: "POST",
      body: data,
    });
  },

  /** List intake registry entries */
  listIntakeRegistry: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    source?: string;
    search?: string;
  }, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.status) query.set("status", params.status);
    if (params?.source) query.set("source", params.source);
    if (params?.search) query.set("search", params.search);
    const qs = query.toString();
    return apiRequest<IntakeRegistryListResponse>(`/data-ingestion/registry${qs ? `?${qs}` : ""}`, { signal });
  },

  /** Get single registry entry */
  getIntakeEntry: (entryId: string) =>
    apiRequest<IntakeRegistryEntry>(`/data-ingestion/registry/${entryId}`),

  /** Get preview for a registry entry */
  getIntakePreview: (entryId: string, page = 1) =>
    apiRequest<IntakePreviewResponse>(`/data-ingestion/registry/${entryId}/preview?page=${page}`),

  /** Prepare extraction for a registry entry */
  prepareExtraction: (entryId: string) =>
    apiRequest<ExtractNavigationResponse>(`/data-ingestion/registry/${entryId}/extract`, { method: "POST" }),

  /** Hard delete a registry entry and all associated data */
  deleteIntakeEntry: (entryId: string) =>
    apiRequest<DeleteResponse>(`/data-ingestion/registry/${entryId}`, { method: "DELETE" }),

  /** Check for duplicates before uploading */
  checkDuplicate: (file: File) => {
    const data = new FormData();
    data.append("file", file);
    return apiRequest<CheckDuplicateResponse>("/data-ingestion/check-duplicate", {
      method: "POST",
      body: data,
    });
  },

  /** Get audit events for a registry entry */
  getIntakeEvents: (entryId: string) =>
    apiRequest<IntakeEventResponse[]>(`/data-ingestion/registry/${entryId}/events`),

  /** Get real-time batch upload progress */
  getBatchProgress: (batchId: string) =>
    apiRequest<BatchProgressResponse>(`/data-ingestion/batches/${batchId}/progress`),

  /** Retry extraction for a failed registry entry */
  retryExtraction: (entryId: string) =>
    apiRequest<RetryExtractionResponse>(`/data-ingestion/registry/${entryId}/retry-extraction`, { method: "POST" }),

  /** Bulk delete multiple registry entries */
  bulkDeleteIntakeEntries: (entryIds: string[]) =>
    apiRequest<BulkDeleteResponse>("/data-ingestion/registry/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ entry_ids: entryIds }),
    }),
};
