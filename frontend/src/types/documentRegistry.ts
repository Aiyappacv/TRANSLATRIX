import type { ExtractionJson, FileProcessingLog, OcrResult } from "./file";

export interface DocumentRegistryEntry {
  id: string;
  originalFileName: string;
  documentType: string | null;
  sourceChannel: string | null;
  intakeRegistryId?: string | null;
  uploadedAt: string | null;
  processedAt: string | null;
  uploadedBy: string | null;
  status: string;
  extractionStatus: string | null;
  ocrEngine: string | null;
  processingTimeSeconds: number | null;
  totalPages: number | null;
  languageDetected: string | null;
  overallConfidence: number | null;
  ocrConfidence: number | null;
  fieldExtractionConfidence: number | null;
  validationScore: number | null;
  invoiceNumber: string | null;
  vendorName: string | null;
  customerName: string | null;
  filingNumber: string | null;
  shipmentReference: string | null;
  country: string | null;
  tradeLane: string | null;
  registryCreatedAt: string | null;
  lastUpdatedAt: string | null;
  processingJobId: string | null;
  versionNumber: number;
  checksum: string | null;
  sizeBytes: number | null;
}

export interface DocumentRegistryDetail extends DocumentRegistryEntry {
  processingLogs: FileProcessingLog[];
  ocr?: OcrResult;
  extractedText?: string;
  extractedTables?: unknown[];
  extractionJson: ExtractionJson | null;
}

export interface DocumentRegistryListResponse {
  entries: DocumentRegistryEntry[];
  total: number;
}
