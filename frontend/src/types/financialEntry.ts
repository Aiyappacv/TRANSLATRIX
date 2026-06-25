export type FinancialCategory = "Expenses" | "Income" | "Assets" | "Liabilities";
export type EntryStatus = "needs_review" | "in_review" | "reviewed" | "ready_for_approval" | "changes_requested" | "rejected" | "validation_failed" | "approved" | "sap_posted" | "sap_failed" | "processing";
export type ValidationStatus = "valid" | "warning" | "failed";
export type AccountingLineType = "debit" | "credit";

export interface ValidationIssue {
  code: string;
  severity: "error" | "warning" | "info";
  message: string;
  field?: string;
}

export interface AccountingLine {
  id: string;
  type: AccountingLineType;
  glAccount: string;
  accountName: string;
  costCenter?: string;
  taxCode?: string;
  amount: number;
  currency: string;
  memo: string;
}

export interface SapMappingSuggestion {
  sapTCode: string;
  postingProcess: string;
  accountingSoftwareAction: string;
  glSuggestion: string;
  confidence: number;
  reason: string;
}

export interface FinancialEntry {
  id: string;
  entryId: string;
  fileId: string;
  sourceFile: string;
  sourceBatch: string;
  sourcePage?: number;
  sourceRow?: number;
  vendor?: string;
  customer?: string;
  originalDescription: string;
  englishDescription: string;
  description: string;
  reference: string;
  referenceNumber: string;
  invoiceNumber?: string;
  gstVatNumber?: string;
  dueDate?: string;
  subtotal?: number;
  taxAmount?: number;
  taxRate?: number;
  taxRates?: number[];
  lineItems?: Array<{ description: string; quantity?: number; lineTotal: number }>;
  date: string;
  amount: number;
  currency: string;
  category: FinancialCategory;
  subcategory: string;
  glAccount: string;
  glSuggestion: string;
  costCenter?: string;
  taxCode?: string;
  sapTCode: string;
  postingProcess: string;
  accountingSoftwareAction: string;
  operation: string;
  status: EntryStatus;
  validationStatus: ValidationStatus;
  reviewer?: string;
  assignedTo?: string;
  confidence: {
    ocr: number;
    classification: number;
    mapping: number;
    overall: number;
  };
  classificationReason: string;
  mappingSuggestion: SapMappingSuggestion;
  accountingEntry: {
    header: {
      documentType: string;
      companyCode: string;
      postingDate: string;
      documentDate: string;
      reference: string;
      headerText: string;
    };
    debitLines: AccountingLine[];
    creditLines: AccountingLine[];
  };
  issues: ValidationIssue[];
}
