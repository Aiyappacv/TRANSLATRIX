export interface AccountingPayloadLine {
  type: "GL" | "VENDOR" | "CUSTOMER" | "ASSET" | "TAX";
  account: string;
  debit: number;
  credit: number;
  costCenter?: string;
  profitCenter?: string;
}

export interface AccountingEntryPayload {
  tenant_id: string;
  company_id: string;
  entry_id: string;
  category: string;
  posting_type: string;
  header: {
    posting_date: string;
    document_date: string;
    currency: string;
    reference: string;
  };
  parties: {
    vendor_code?: string | null;
    customer_code?: string | null;
  };
  lines: AccountingPayloadLine[];
}
