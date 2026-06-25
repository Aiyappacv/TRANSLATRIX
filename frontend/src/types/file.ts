import type { OperationalStatus } from "@/utils/status";

export type FilePreviewKind = "pdf" | "image" | "spreadsheet" | "docx" | "text" | "unsupported";
export type WorkerStatus = "completed" | "processing" | "queued" | "failed" | "retrying";

export interface OcrBlock {
  id: string;
  type: "text" | "table" | "amount" | "metadata" | "date" | "tax" | "vendor";
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
  pageNumber: number;
}

export interface OcrPage {
  pageNumber: number;
  width: number;
  height: number;
  confidence: number;
  detectedLanguage: string;
  blocks: OcrBlock[];
}

export interface OcrResult {
  engine: "mistral_ocr" | "paddleocr" | "azure_document_intelligence" | "aws_textract" | "google_document_ai" | "direct_parser";
  engineVersion: string;
  status: WorkerStatus;
  languageDetected: string;
  overallConfidence: number;
  pageCount: number;
  startedAt: string;
  completedAt?: string;
  pages: OcrPage[];
}

export interface ExtractedTableCell {
  id: string;
  rowIndex: number;
  columnIndex: number;
  value: string;
  correctedValue?: string;
  confidence: number;
  bbox?: [number, number, number, number];
}

export interface ExtractedTable {
  id: string;
  name: string;
  pageNumber: number;
  confidence: number;
  headers: string[];
  rows: ExtractedTableCell[][];
}

export interface FileProcessingLog {
  id: string;
  step: string;
  worker: string;
  status: WorkerStatus;
  message: string;
  startedAt: string;
  completedAt?: string;
  errorDetails?: string;
  retryable: boolean;
}

export interface FileUploader {
  id: string;
  name: string;
  email: string;
  role: string;
  companyId?: string;
}

export interface IngestedFile {
  id: string;
  name: string;
  fileName: string;
  type: FilePreviewKind;
  mimeType: string;
  sizeBytes: number;
  source: string;
  batchId: string;
  batchName: string;
  status: OperationalStatus;
  ocrStatus: WorkerStatus;
  extractionStatus: WorkerStatus;
  entriesExtracted: number;
  confidence: number;
  sourceLanguage: string;
  extractionMethod: string;
  checksum: string;
  createdAt: string;
  uploadedAt: string;
  uploadedBy?: FileUploader;
  previewUrl?: string;
  spreadsheetRows?: string[][];
  extractedText: string;
  ocr?: OcrResult;
  extractedTables: ExtractedTable[];
  extractionJson?: ExtractionJson;
  extractionConfidence?: number | null;
  fieldConfidence?: Record<string, number>;
  processingStage?: string;
  processingCompletedAt?: string;
  processingLogs: FileProcessingLog[];
  extractionProgress?: ExtractionProgress;
}

export interface ExtractionProgress {
  totalPages: number;
  totalChunks: number;
  completedChunks: number;
  currentStage: "extracting" | "merging" | "validating" | "extracted" | "extraction_failed";
  currentChunk?: string;
  progressPct?: number;
  pagesPerSec?: number | null;
  etaSeconds?: number | null;
  failedChunks?: { chunk_index: number; pages: string; error: string | null; retries: number }[];
  error?: string;
}

export interface TradeFields {
  exporter: string | null;
  importer: string | null;
  buyer: string | null;
  seller: string | null;
  incoterms: string | null;
  country_of_origin: string | null;
  country_of_destination: string | null;
  port_of_loading: string | null;
  port_of_discharge: string | null;
  gross_weight: number | null;
  net_weight: number | null;
  payment_terms: string | null;
  invoice_value: number | null;
}

export interface TransactionInfo {
  transaction_date: string | null;
  reference_date: string | null;
  transaction_code: string | null;
  particulars: string | null;
  cheque_number: string | null;
  debit_amount: number | null;
  credit_amount: number | null;
  running_balance: number | null;
  balance_type: string | null;
}

export interface BankingInfo {
  bank_name: string | null;
  branch_name: string | null;
  account_holder_name: string | null;
  account_number: string | null;
  account_type: string | null;
  statement_period_from: string | null;
  statement_period_to: string | null;
  currency: string | null;
  opening_balance: number | null;
  closing_balance: number | null;
  transactions: TransactionInfo[];
}

export interface SupplierInfo {
  name: string | null;
  gstin: string | null;
  pan: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
}

export interface CustomerInfo {
  name: string | null;
  pan: string | null;
  gstin: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
}

export interface InvoiceDetails {
  invoice_number: string | null;
  invoice_date: string | null;
  document_type: string | null;
  currency: string | null;
}

export interface FinancialSummary {
  gross_amount: number | null;
  discount_amount: number | null;
  gst_amount: number | null;
  cgst_amount: number | null;
  sgst_amount: number | null;
  igst_amount: number | null;
  net_amount: number | null;
  taxable_value: number | null;
  place_of_supply: string | null;
  reverse_charge: boolean | null;
  amount_payable: number | null;
}

export interface LineItem {
  product_name: string | null;
  hsn_code: string | null;
  pack: string | null;
  batch_number: string | null;
  expiry_date: string | null;
  quantity: number | null;
  mrp: number | null;
  rate: number | null;
  gst: number | null;
  taxable_value: number | null;
  cgst: number | null;
  sgst: number | null;
  igst: number | null;
  line_total: number | null;
  confidence: number | null;
}

export interface ExtractionMetadata {
  page_count: number | null;
  language: string | null;
  file_type: string | null;
  uploaded_by: string | null;
  storage_path: string | null;
}

export interface FieldConfidence {
  field: string;
  value: unknown;
  confidence: number;
  status: string;
  source?: string | null;
  page?: number | null;
}

export interface ProcessingMetrics {
  ocr_engine: string | null;
  extraction_engine: string | null;
  pages_processed: number | null;
  fields_extracted: number | null;
  tables_extracted: number | null;
  average_confidence: number | null;
  processing_time_seconds: number | null;
  preprocessing_applied: boolean;
  layout_analysis_applied: boolean;
  table_extraction_applied: boolean;
  validation_applied: boolean;
}

export interface ValidationResultItem {
  field: string;
  value: unknown;
  valid: boolean;
  confidence: number;
  message: string | null;
  corrected_value: unknown;
  severity: string;
}

export interface LayoutRegion {
  type: string;
  bbox: [number, number, number, number];
  text: string;
  confidence: number;
  pageNumber: number;
}

export interface ExtractionJson {
  document_id: string | null;
  document_type: string | null;
  document_name: string | null;
  processing_timestamp: string | null;
  ocr_engine: string | null;
  overall_confidence: number | null;
  status: string;
  supplier: SupplierInfo | null;
  customer: CustomerInfo | null;
  invoice_details: InvoiceDetails | null;
  financial_summary: FinancialSummary | null;
  line_items: LineItem[] | null;
  trade_fields: TradeFields | null;
  banking_info: BankingInfo | null;
  metadata: ExtractionMetadata | null;
  confidence_details?: FieldConfidence[];
  raw_ocr_text: string | null;
  processing_metrics?: ProcessingMetrics | null;
  validation_results?: ValidationResultItem[];
  layout_regions?: LayoutRegion[];
  extracted_tables?: Record<string, unknown>[];
}

export interface MultiPageDocument {
  documents: ExtractionJson[];
}
