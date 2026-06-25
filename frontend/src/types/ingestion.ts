export type SharedLinkProvider =
  | "Google Drive"
  | "OneDrive"
  | "SharePoint"
  | "Dropbox"
  | "SFTP"
  | "AWS S3"
  | "Azure Blob"
  | "Manual URL"
  | "Local Upload";

export type SharedLinkAuthType = "None" | "OAuth" | "Service Account" | "API Key" | "Basic Auth" | "SFTP Key" | "SAS Token";
export type SharedLinkScheduleMode = "Manual" | "Hourly" | "Every 2 hours" | "Daily" | "Weekly";

export interface FileDiscoveryItem {
  id: string;
  fileName: string;
  path: string;
  mimeType: string;
  sizeBytes: number;
  status: "supported" | "unsupported" | "duplicate" | "failed";
  reason?: string;
  discoveredAt: string;
}

export interface LinkValidationResult {
  accessible: boolean;
  filesFound: number;
  supportedFilesCount: number;
  unsupportedFilesCount: number;
  estimatedProcessingTime: string;
  securityWarning?: string;
  latencyMs: number;
  discoveredFiles: FileDiscoveryItem[];
}

export interface SharedLinkSource {
  id: string;
  clientName: string;
  name: string;
  provider: SharedLinkProvider;
  sourceType: SharedLinkProvider;
  url: string;
  authenticationType: SharedLinkAuthType;
  folderPath: string;
  fileFilters: string;
  schedule: SharedLinkScheduleMode | string;
  defaultCompanyCode: string;
  defaultCurrency: string;
  defaultReviewerGroup: string;
  defaultAccountingIntegration: string;
  allowedDomain: string;
  status: "active" | "paused" | "failed" | "draft";
  lastSyncAt: string;
  filesDiscovered: number;
  owner: string;
  validation: LinkValidationResult;
}

export interface PreprocessingMetadata {
  filename: string;
  extension: string;
  mimeType: string;
  sizeBytes: number;
  checksum: string;
  checksumAlgorithm: string;
  isImage: boolean;
  isPdf: boolean;
  isSpreadsheet: boolean;
  isDocument: boolean;
  pageCount: number;
  wordCount: number;
  hasText: boolean;
  languageHint: string | null;
  structure: string;
  detectedAt: string;
  preprocessingStartedAt: string;
}

export interface TierEntry {
  storageKey: string;
  id: string;
}

export interface PreprocessingResult {
  fileId: string;
  filename: string;
  metadata: PreprocessingMetadata;
  tiers: {
    raw: TierEntry;
    processed: TierEntry;
    curated: TierEntry;
  };
  durationMs: number;
}

export interface DedupMatch {
  fileId: string;
  filename: string;
  similarity: number;
  method: string;
}

export interface DedupResult {
  isDuplicate: boolean;
  similarityScore: number;
  matches: DedupMatch[];
  embeddingId: string | null;
}

export interface PreviewPage {
  pageNumber: number;
  imageUrl: string;
  width: number;
  height: number;
}

export interface PreviewInfo {
  fileId: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  totalPages: number;
  pages: PreviewPage[];
  previewToken: string;
  expiresAt: string;
}

export interface ExtractedField {
  name: string;
  value: unknown;
  confidence: number;
  pageNumber?: number;
  bbox?: Record<string, number>;
}

export interface ExtractionResult {
  fileId: string;
  filename: string;
  fields: ExtractedField[];
  rawText: string;
  confidence: number;
  processingTimeMs: number;
  ocrEngine: string;
}

export interface ExtractionJobResponse {
  jobId: string;
  fileId: string;
  status: string;
  result: ExtractionResult | null;
  error: string | null;
}

export interface LakeTierRecord {
  id: string;
  fileId: string;
  tier: string;
  storageKey: string;
  checksum: string;
  contentType: string | null;
  sizeBytes: number;
  metadataJson: Record<string, unknown> | null;
  createdAt: string;
}

export interface ProcessingAuditEntry {
  id: string;
  fileId: string;
  step: string;
  status: string;
  message: string | null;
  durationMs: number | null;
  metadataJson: Record<string, unknown> | null;
  createdAt: string;
}

export interface ExportRequest {
  fileIds: string[];
  includeRawText?: boolean;
  includeMetadata?: boolean;
  includeConfidence?: boolean;
}

export interface ExportFileEntry {
  fileId: string;
  filename: string;
  extractedAt: string;
  fields: ExtractedField[];
  rawText?: string;
  metadata?: Record<string, unknown>;
}

export interface ExportResponse {
  exportId: string;
  exportedAt: string;
  totalFiles: number;
  files: ExportFileEntry[];
  jsonPayload: string;
}

// ── Data Intake / Enterprise Ingestion Module ────────────────

export type SourceChannel = "portal" | "api" | "email" | "sftp" | "barcode" | "voice";

export type IntakeDocumentStatus =
  | "uploading"
  | "uploaded"
  | "metadata_processing"
  | "metadata_ready"
  | "ready_for_extraction"
  | "extracting"
  | "extracted"
  | "failed";

export interface IntakeRegistryEntry {
  id: string;
  file_id: string | null;
  original_filename: string;
  source_channel: string;
  document_type: string | null;
  language: string | null;
  status: string;
  tier: string | null;
  is_duplicate: boolean;
  duplicate_of_id: string | null;
  duplicate_similarity: number | null;
  checksum: string | null;
  file_size: number;
  mime_type: string | null;
  page_count: number | null;
  language_detected: string | null;
  orientation: string | null;
  processing_metadata: Record<string, unknown> | null;
  created_at: string;
  processed_at: string | null;
}

export interface IntakeRegistryListResponse {
  entries: IntakeRegistryEntry[];
  total: number;
}

export interface DuplicateMatch {
  file_id: string;
  registry_id: string | null;
  filename: string;
  similarity: number;
  method: string;
  uploaded_at: string | null;
}

export interface DuplicateWarning {
  is_exact_duplicate: boolean;
  is_semantic_duplicate: boolean;
  similarity_score: number;
  matches: DuplicateMatch[];
}

export interface UploadResponse {
  entry: IntakeRegistryEntry;
  status: string;
  message: string;
}

export interface CheckDuplicateResponse {
  is_exact_duplicate: boolean;
  is_semantic_duplicate: boolean;
  similarity_score: number;
  matches: DuplicateMatch[];
}

export interface PreviewPageInfo {
  page_number: number;
  image_url: string;
  width: number;
  height: number;
}

export interface IntakePreviewResponse {
  entry_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  total_pages: number;
  pages: PreviewPageInfo[];
}

export interface ExtractNavigationResponse {
  file_id: string;
  entry_id: string;
  redirect_url: string;
}

export interface DeleteResponse {
  deleted: boolean;
  message: string;
}

export interface BulkDeleteResponse {
  deleted: number;
  message: string;
}

export interface IntakeEventResponse {
  id: string;
  registry_id: string;
  event_type: string;
  status: string;
  message: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface BatchJobProgress {
  job_id: string;
  job_type: string;
  status: string;
  payload?: Record<string, unknown> | null;
  error?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  file_name?: string | null;
}

export interface BatchProgressResponse {
  batch_id: string;
  total: number;
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  jobs: BatchJobProgress[];
}

export interface BatchUploadResponse {
  batch_id: string;
  total: number;
  accepted: number;
  entries: IntakeRegistryEntry[];
  message: string;
}

export interface RetryExtractionResponse {
  entry_id: string;
  status: string;
  message: string;
}
