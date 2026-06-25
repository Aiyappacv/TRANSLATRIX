import { useMemo, useState } from "react";
import { Check, ChevronDown, ChevronRight, Copy, Download, FileCode, FileText, Search, Table2, X } from "lucide-react";
import { toast } from "sonner";
import type { ExtractionJson } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { cn } from "@/utils/cn";
import { fileApi } from "@/services/fileApi";

function confidenceLevel(score: number): { label: string; className: string } {
  if (score >= 0.95) return { label: "High", className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" };
  if (score >= 0.8) return { label: "Medium", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" };
  return { label: "Review", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" };
}

function LowConfidenceBadge({ score }: { score: number }) {
  const level = confidenceLevel(score);
  return <Badge className={cn("text-xs", level.className)}>{level.label}</Badge>;
}

function JsonValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) return <span className="text-slate-400">null</span>;
  if (typeof value === "string") return <span className="text-emerald-600 dark:text-emerald-400">"{value}"</span>;
  if (typeof value === "number") return <span className="text-blue-600 dark:text-blue-400">{value}</span>;
  if (typeof value === "boolean") return <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-slate-400">[]</span>;
    return (
      <span className="block">
        <span className="text-slate-500">[</span>
        <span className="block pl-4">
          {value.map((item, i) => (
            <span key={i} className="block">
              <JsonValue value={item} depth={depth + 1} />
              {i < value.length - 1 ? <span className="text-slate-400">,</span> : null}
            </span>
          ))}
        </span>
        <span className="text-slate-500">]</span>
      </span>
    );
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-slate-400">{`{}`}</span>;
    return (
      <span className="block">
        <span className="text-slate-500">{`{`}</span>
        <span className="block pl-4">
          {entries.map(([key, val]) => (
            <span key={key} className="block">
              <span className="text-indigo-600 dark:text-indigo-400">"{key}"</span>: <JsonValue value={val} depth={depth + 1} />
            </span>
          ))}
        </span>
        <span className="text-slate-500">{`}`}</span>
      </span>
    );
  }
  return <span>{String(value)}</span>;
}

interface SectionProps {
  title: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  confidence?: number;
}

function CollapsibleSection({ title, icon, defaultOpen = true, children, confidence }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900"
      >
        <span className="flex items-center gap-2">
          {icon}
          {title}
          {confidence !== undefined ? <LowConfidenceBadge score={confidence} /> : null}
        </span>
        {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
      </button>
      {open ? <div className="border-t border-slate-200 px-4 py-3 dark:border-slate-800">{children}</div> : null}
    </div>
  );
}

function FieldRow({ label, value, confidence, sub }: { label: string; value: string | number | null | undefined; confidence?: number; sub?: string }) {
  const display = value === null || value === undefined || value === "" || value === 0 ? <span className="text-slate-400">—</span> : <span>{value}</span>;
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900">
      <span className="flex items-center gap-2 font-medium text-slate-500 dark:text-slate-400">
        {label}
        {sub ? <span className="text-xs text-slate-400">({sub})</span> : null}
      </span>
      <div className="flex items-center gap-3">
        <span>{display}</span>
        {confidence !== undefined ? <LowConfidenceBadge score={confidence} /> : null}
      </div>
    </div>
  );
}

function ExtractedTablesSection({ tables }: { tables: Record<string, unknown>[] }) {
  if (!tables || tables.length === 0) return null;
  return (
    <div className="space-y-4">
      {tables.map((table, ti) => {
        const headers = table.headers as string[] | undefined;
        const rows = table.rows as Record<string, string>[] | undefined;
        if (!headers || !rows || rows.length === 0) return null;
        return (
          <div key={ti} className="rounded-xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2 dark:border-slate-800">
              <Table2 className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Table {ti + 1}</span>
              <Badge variant="neutral" className="ml-auto text-xs">{rows.length} rows</Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium text-slate-500 dark:border-slate-800 dark:bg-slate-900">
                    {headers.map((h, hi) => (
                      <th key={hi} className="px-3 py-2">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, ri) => (
                    <tr key={ri} className="border-b border-slate-100 text-sm dark:border-slate-800/50">
                      {headers.map((h, ci) => {
                        const cell = row[ci] ?? row[`col_${ci}`] ?? "";
                        return <td key={ci} className="px-3 py-2 text-slate-600 dark:text-slate-400">{String(cell)}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LayoutRegionsSection({ regions }: { regions: ExtractionJson["layout_regions"] }) {
  if (!regions || regions.length === 0) return null;
  return (
    <div className="space-y-2">
      {regions.map((r, i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900">
          <Badge variant="neutral" className="shrink-0 text-xs capitalize">{r.type}</Badge>
          <div className="flex-1">
            <p className="text-xs text-slate-500">{r.text?.slice(0, 200) || "—"}</p>
            <span className="text-xs text-slate-400">
              Confidence: {Math.round(r.confidence * 100)}% | Page {r.pageNumber}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

interface ExtractionJsonViewerProps {
  json: ExtractionJson | null;
  loading?: boolean;
  fileId?: string;
}

export function ExtractionJsonViewer({ json, loading, fileId }: ExtractionJsonViewerProps) {
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState(false);
  const [rawView, setRawView] = useState(false);

  const cleanJson = useMemo(() => {
    if (!json) return {};
    return Object.fromEntries(
      Object.entries({
        document_id: json.document_id,
        document_type: json.document_type,
        document_name: json.document_name,
        supplier: json.supplier,
        customer: json.customer,
        invoice_details: json.invoice_details,
        financial_summary: json.financial_summary,
        trade_fields: json.trade_fields,
        banking_info: json.banking_info,
        line_items: json.line_items,
        extracted_tables: json.extracted_tables,
      }).filter(([, v]) => v != null && !(typeof v === "object" && (Array.isArray(v) ? v.length === 0 : Object.keys(v).length === 0)))
    );
  }, [json]);

  const prettyJson = useMemo(() => {
    if (!json) return "";
    try {
      return JSON.stringify(cleanJson, null, 2);
    } catch {
      return String(json);
    }
  }, [cleanJson, json]);

  const filteredPrettyJson = useMemo(() => {
    if (!search) return prettyJson;
    const lower = search.toLowerCase();
    return prettyJson
      .split("\n")
      .filter((line) => line.toLowerCase().includes(lower))
      .join("\n");
  }, [prettyJson, search]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prettyJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = prettyJson;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Extraction JSON</CardTitle>
          <CardDescription>Loading structured extraction results...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!json) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Extraction JSON</CardTitle>
          <CardDescription>No structured extraction data available. Process the document to generate JSON.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-4 py-12 text-center">
            <FileCode className="h-16 w-16 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500 dark:text-slate-400">Run document processing to generate a structured JSON representation of the extracted data.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (json.status === "ocr_only") {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extraction JSON</span>
            <Badge variant="neutral">OCR only</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {fileId ? (
              <Button variant="outline" size="sm" onClick={() => {
                fileApi.downloadExtractionJson(fileId, `extraction_${fileId.slice(0, 8)}.json`)
                  .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
              }}>
                <Download className="mr-1.5 h-3.5 w-3.5" />
                Download JSON
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={handleCopy}>
              {copied ? <Check className="mr-1.5 h-3.5 w-3.5 text-emerald-500" /> : <Copy className="mr-1.5 h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy JSON"}
            </Button>
          </div>
        </div>

        <Card className="border-amber-200 dark:border-amber-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-600">
              <FileText className="h-5 w-5" />
              Generated from OCR Results
            </CardTitle>
            <CardDescription>
              Structured field extraction was not available. Showing raw OCR output with layout analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>

            {json.extracted_tables && json.extracted_tables.length > 0 ? (
              <div className="mb-4">
                <h4 className="mb-2 text-sm font-semibold text-slate-600 dark:text-slate-400">Detected Tables</h4>
                <ExtractedTablesSection tables={json.extracted_tables} />
              </div>
            ) : null}
            {json.layout_regions && json.layout_regions.length > 0 ? (
              <div className="mb-4">
                <h4 className="mb-2 text-sm font-semibold text-slate-600 dark:text-slate-400">Detected Layout Regions</h4>
                <LayoutRegionsSection regions={json.layout_regions} />
              </div>
            ) : null}
            {json.raw_ocr_text ? (
              <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">
                {json.raw_ocr_text}
              </pre>
            ) : (
              <p className="text-sm text-slate-400">No OCR text available.</p>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const sectionConfidence = (key: string): number | undefined => {
    if (!json.confidence_details) return undefined;
    const found = json.confidence_details.find((d) => d.field === key);
    return found?.confidence;
  };

  const fmtNum = (val: number | null | undefined, currency?: string | null): string => {
    if (val == null) return "—";
    return `${currency ?? ""} ${val.toFixed(2)}`;
  };

  return (
    <div className="space-y-4">
      {/* Summary toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Extraction JSON</span>
          <Badge variant="neutral">{json.document_id ? json.document_id.slice(0, 8) : "—"}</Badge>

        </div>
        <div className="flex flex-wrap items-center gap-2">
          {fileId ? (
            <Button variant="default" size="sm" onClick={() => {
              fileApi.downloadExtractionSummary(fileId, `extraction_summary_${fileId.slice(0, 8)}.json`)
                .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
            }}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Download JSON
            </Button>
          ) : null}
          {fileId ? (
            <Button variant="outline" size="sm" onClick={() => {
              fileApi.downloadExtractionJson(fileId, `extraction_${fileId.slice(0, 8)}.json`)
                .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
            }}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Download Business Data
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={() => setRawView(!rawView)}>
            <FileCode className="mr-1.5 h-3.5 w-3.5" />
            {rawView ? "Structured" : "Raw JSON"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="mr-1.5 h-3.5 w-3.5 text-emerald-500" /> : <Copy className="mr-1.5 h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy JSON"}
          </Button>
        </div>
      </div>



      {/* Raw JSON view */}
      {rawView ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Raw JSON</CardTitle>
              <CardDescription>Pretty-printed extraction result.</CardDescription>
            </div>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search JSON..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
              {search ? (
                <button type="button" onClick={() => setSearch("")} className="absolute right-2.5 top-2.5">
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">
              {filteredPrettyJson || prettyJson}
            </pre>
          </CardContent>
        </Card>
      ) : (
        /* Structured view */
        <div className="space-y-3">
          {/* Document overview */}
          <CollapsibleSection title="Document Overview" defaultOpen={true}>
            <div className="space-y-2">
              <FieldRow label="Document ID" value={json.document_id} />
              <FieldRow label="Document Name" value={json.document_name} />
              <FieldRow label="Document Type" value={json.document_type} />
            </div>
          </CollapsibleSection>

          {/* Supplier */}
          {json.supplier ? (
            <CollapsibleSection title="Supplier Information" defaultOpen={true} confidence={sectionConfidence("vendor")}>
              <div className="space-y-2">
                <FieldRow label="Name" value={json.supplier.name} confidence={sectionConfidence("vendor")} />
                <FieldRow label="GSTIN" value={json.supplier.gstin} confidence={sectionConfidence("gst_vat_number")} />
                {json.supplier.pan ? <FieldRow label="PAN" value={json.supplier.pan} /> : null}
                <FieldRow label="Address" value={json.supplier.address} />
                <FieldRow label="Phone" value={json.supplier.phone} />
                <FieldRow label="Email" value={json.supplier.email} />
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Customer */}
          {json.customer ? (
            <CollapsibleSection title="Customer Information" defaultOpen={true} confidence={sectionConfidence("customer")}>
              <div className="space-y-2">
                <FieldRow label="Name" value={json.customer.name} confidence={sectionConfidence("customer")} />
                <FieldRow label="GSTIN" value={json.customer.gstin} />
                {json.customer.pan ? <FieldRow label="PAN" value={json.customer.pan} /> : null}
                <FieldRow label="Address" value={json.customer.address} />
                <FieldRow label="Phone" value={json.customer.phone} />
                {json.customer.email ? <FieldRow label="Email" value={json.customer.email} /> : null}
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Invoice Details */}
          {json.invoice_details ? (
            <CollapsibleSection title="Invoice Details" defaultOpen={true} confidence={sectionConfidence("invoice_number")}>
              <div className="space-y-2">
                <FieldRow label="Invoice Number" value={json.invoice_details.invoice_number} confidence={sectionConfidence("invoice_number")} />
                <FieldRow label="Invoice Date" value={json.invoice_details.invoice_date} confidence={sectionConfidence("invoice_date")} />
                <FieldRow label="Document Type" value={json.invoice_details.document_type} />
                <FieldRow label="Currency" value={json.invoice_details.currency} confidence={sectionConfidence("currency")} />
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Financial Summary */}
          {json.financial_summary ? (
            <CollapsibleSection title="Financial Summary" defaultOpen={true} confidence={sectionConfidence("total")}>
              <div className="grid gap-2 sm:grid-cols-2">
                <FieldRow label="Gross Amount" value={fmtNum(json.financial_summary.gross_amount, json.invoice_details?.currency)} confidence={sectionConfidence("total")} />
                <FieldRow label="Discount" value={fmtNum(json.financial_summary.discount_amount, json.invoice_details?.currency)} />
                <FieldRow label="Taxable Value" value={fmtNum(json.financial_summary.taxable_value, json.invoice_details?.currency)} />
                <FieldRow label="GST Amount" value={fmtNum(json.financial_summary.gst_amount, json.invoice_details?.currency)} confidence={sectionConfidence("tax_amount")} />
                <FieldRow label="CGST Amount" value={fmtNum(json.financial_summary.cgst_amount, json.invoice_details?.currency)} />
                <FieldRow label="SGST Amount" value={fmtNum(json.financial_summary.sgst_amount, json.invoice_details?.currency)} />
                <FieldRow label="IGST Amount" value={fmtNum(json.financial_summary.igst_amount, json.invoice_details?.currency)} />
                <FieldRow label="Net Amount" value={fmtNum(json.financial_summary.net_amount, json.invoice_details?.currency)} confidence={sectionConfidence("subtotal")} />
                {json.financial_summary.place_of_supply ? <FieldRow label="Place of Supply" value={json.financial_summary.place_of_supply} /> : null}
                {json.financial_summary.reverse_charge != null ? <FieldRow label="Reverse Charge" value={json.financial_summary.reverse_charge ? "Yes" : "No"} /> : null}
                {json.financial_summary.amount_payable != null ? <FieldRow label="Amount Payable" value={fmtNum(json.financial_summary.amount_payable, json.invoice_details?.currency)} /> : null}
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Trade Fields (exporter, incoterms, ports, etc.) */}
          {json.trade_fields && (json.trade_fields.exporter || json.trade_fields.incoterms || json.trade_fields.country_of_origin) ? (
            <CollapsibleSection title="Trade / Shipping" defaultOpen={false}>
              <div className="grid gap-2 sm:grid-cols-2">
                {json.trade_fields.exporter ? <FieldRow label="Exporter" value={json.trade_fields.exporter} /> : null}
                {json.trade_fields.importer ? <FieldRow label="Importer" value={json.trade_fields.importer} /> : null}
                {json.trade_fields.buyer ? <FieldRow label="Buyer" value={json.trade_fields.buyer} /> : null}
                {json.trade_fields.seller ? <FieldRow label="Seller" value={json.trade_fields.seller} /> : null}
                {json.trade_fields.incoterms ? <FieldRow label="Incoterms" value={json.trade_fields.incoterms} /> : null}
                {json.trade_fields.country_of_origin ? <FieldRow label="Country of Origin" value={json.trade_fields.country_of_origin} /> : null}
                {json.trade_fields.country_of_destination ? <FieldRow label="Country of Destination" value={json.trade_fields.country_of_destination} /> : null}
                {json.trade_fields.port_of_loading ? <FieldRow label="Port of Loading" value={json.trade_fields.port_of_loading} /> : null}
                {json.trade_fields.port_of_discharge ? <FieldRow label="Port of Discharge" value={json.trade_fields.port_of_discharge} /> : null}
                {json.trade_fields.gross_weight != null ? <FieldRow label="Gross Weight" value={`${json.trade_fields.gross_weight} kg`} /> : null}
                {json.trade_fields.net_weight != null ? <FieldRow label="Net Weight" value={`${json.trade_fields.net_weight} kg`} /> : null}
                {json.trade_fields.payment_terms ? <FieldRow label="Payment Terms" value={json.trade_fields.payment_terms} /> : null}
                {json.trade_fields.invoice_value != null ? <FieldRow label="Invoice Value" value={fmtNum(json.trade_fields.invoice_value, json.invoice_details?.currency)} /> : null}
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Banking Info */}
          {json.banking_info && (json.banking_info.bank_name || json.banking_info.account_number || json.banking_info.transactions?.length > 0) ? (
            <>
              <CollapsibleSection title="Banking Details" defaultOpen={true}>
                <div className="grid gap-2 sm:grid-cols-2">
                  <FieldRow label="Bank Name" value={json.banking_info.bank_name} />
                  <FieldRow label="Branch" value={json.banking_info.branch_name} />
                  <FieldRow label="Account Holder" value={json.banking_info.account_holder_name} />
                  <FieldRow label="Account Number" value={json.banking_info.account_number} />
                  <FieldRow label="Account Type" value={json.banking_info.account_type} />
                  <FieldRow label="Statement Period" value={json.banking_info.statement_period_from ? `${json.banking_info.statement_period_from} → ${json.banking_info.statement_period_to ?? "—"}` : null} />
                  <FieldRow label="Currency" value={json.banking_info.currency} />
                  <FieldRow label="Opening Balance" value={json.banking_info.opening_balance != null ? fmtNum(json.banking_info.opening_balance, json.banking_info.currency) : null} />
                  <FieldRow label="Closing Balance" value={json.banking_info.closing_balance != null ? fmtNum(json.banking_info.closing_balance, json.banking_info.currency) : null} />
                </div>
              </CollapsibleSection>

              {/* Transactions */}
              {json.banking_info.transactions && json.banking_info.transactions.length > 0 ? (
                <CollapsibleSection title={`Transactions (${json.banking_info.transactions.length})`} defaultOpen={false}>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-medium text-slate-500 dark:border-slate-800 dark:bg-slate-900">
                          <th className="px-2 py-1">Date</th>
                          <th className="px-2 py-1">Ref Date</th>
                          <th className="px-2 py-1">Code</th>
                          <th className="px-2 py-1">Particulars</th>
                          <th className="px-2 py-1">Cheque</th>
                          <th className="px-2 py-1">Debit</th>
                          <th className="px-2 py-1">Credit</th>
                          <th className="px-2 py-1">Balance</th>
                          <th className="px-2 py-1">Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {json.banking_info.transactions.map((txn, i) => (
                          <tr key={i} className="border-b border-slate-100 text-xs dark:border-slate-800/50">
                            <td className="px-2 py-1 whitespace-nowrap">{txn.transaction_date ?? "—"}</td>
                            <td className="px-2 py-1 whitespace-nowrap">{txn.reference_date ?? "—"}</td>
                            <td className="px-2 py-1">{txn.transaction_code ?? "—"}</td>
                            <td className="px-2 py-1 max-w-[200px] truncate" title={txn.particulars ?? ""}>{txn.particulars ?? "—"}</td>
                            <td className="px-2 py-1">{txn.cheque_number ?? "—"}</td>
                            <td className="px-2 py-1 text-right tabular-nums text-red-600">{txn.debit_amount != null ? txn.debit_amount.toFixed(2) : "—"}</td>
                            <td className="px-2 py-1 text-right tabular-nums text-emerald-600">{txn.credit_amount != null ? txn.credit_amount.toFixed(2) : "—"}</td>
                            <td className="px-2 py-1 text-right tabular-nums">{txn.running_balance != null ? txn.running_balance.toFixed(2) : "—"}</td>
                            <td className="px-2 py-1">{txn.balance_type ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CollapsibleSection>
              ) : null}
            </>
          ) : null}

          {/* Line Items */}
          {json.line_items && json.line_items.length > 0 ? (
            <CollapsibleSection
              title={`Line Items (${json.line_items.length})`}
              defaultOpen={false}
              confidence={sectionConfidence("line_items")}
            >
              <div className="space-y-3">
                {json.line_items.map((item, i) => (
                  <div key={i} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{item.product_name || `Item ${i + 1}`}</span>
                      {item.confidence != null ? <LowConfidenceBadge score={item.confidence} /> : null}
                    </div>
                    <div className="grid gap-1.5 text-xs sm:grid-cols-3">
                      {item.hsn_code ? <FieldRow label="HSN" value={item.hsn_code} /> : null}
                      {item.pack ? <FieldRow label="Pack" value={item.pack} /> : null}
                      {item.batch_number ? <FieldRow label="Batch" value={item.batch_number} /> : null}
                      {item.expiry_date ? <FieldRow label="Expiry" value={item.expiry_date} /> : null}
                      {item.quantity != null ? <FieldRow label="Qty" value={item.quantity} /> : null}
                      {item.mrp != null ? <FieldRow label="MRP" value={item.mrp} /> : null}
                      {item.rate != null ? <FieldRow label="Rate" value={item.rate} /> : null}
                      {item.gst != null ? <FieldRow label="GST%" value={item.gst} /> : null}
                      {item.taxable_value != null ? <FieldRow label="Taxable" value={item.taxable_value} /> : null}
                      {item.cgst != null ? <FieldRow label="CGST" value={item.cgst} /> : null}
                      {item.sgst != null ? <FieldRow label="SGST" value={item.sgst} /> : null}
                      {item.igst != null ? <FieldRow label="IGST" value={item.igst} /> : null}
                      {item.line_total != null ? <FieldRow label="Total" value={item.line_total} /> : null}
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Extracted Tables */}
          {json.extracted_tables && json.extracted_tables.length > 0 ? (
            <CollapsibleSection title={`Extracted Tables (${json.extracted_tables.length})`} defaultOpen={false} icon={<Table2 className="h-4 w-4 text-slate-400" />}>
              <ExtractedTablesSection tables={json.extracted_tables} />
            </CollapsibleSection>
          ) : null}
        </div>
      )}
    </div>
  );
}
