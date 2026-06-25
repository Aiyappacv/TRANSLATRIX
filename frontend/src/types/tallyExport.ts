export type TallyExportFormat = "xml" | "json" | "csv";
export type TallyExportStatus = "queued" | "processing" | "completed" | "failed";
export type TallyVoucherType = "purchase" | "sales" | "journal" | "payment" | "receipt" | "contra";

export interface CreateTallyExportRequest {
  companyId: string;
  companyCode: string;
  dateFrom: string;
  dateTo: string;
  format: TallyExportFormat;
  voucherTypes: TallyVoucherType[];
  includeLedgers: boolean;
  includeCostCenters: boolean;
  includeTaxDetails: boolean;
}

export interface TallyExportJob extends CreateTallyExportRequest {
  id: string;
  companyName: string;
  status: TallyExportStatus;
  recordsExported: number;
  retryable: boolean;
  createdAt: string;
  createdBy: string;
  completedAt?: string;
  fileName?: string;
  requestId: string;
  errorMessage?: string;
}

export interface TallyExportDownload {
  exportId: string;
  fileName: string;
  downloadUrl: string;
  expiresAt?: string;
}
