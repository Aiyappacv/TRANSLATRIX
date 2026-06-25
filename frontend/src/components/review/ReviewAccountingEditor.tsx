import { Plus, Trash2 } from "lucide-react";
import type { AccountingLine, FinancialEntry } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatCurrency } from "@/utils/formatters";

interface ReviewAccountingEditorProps {
  value: FinancialEntry["accountingEntry"];
  currency: string;
  disabled?: boolean;
  onChange: (value: FinancialEntry["accountingEntry"]) => void;
}

function createLine(type: AccountingLine["type"], currency: string): AccountingLine {
  return {
    id: `review_line_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    type,
    glAccount: "",
    accountName: "",
    costCenter: "",
    taxCode: "",
    amount: 0,
    currency,
    memo: "",
  };
}

export function ReviewAccountingEditor({ value, currency, disabled, onChange }: ReviewAccountingEditorProps) {
  const debitTotal = value.debitLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
  const creditTotal = value.creditLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
  const balanced = Math.abs(debitTotal - creditTotal) < 0.01;

  const updateHeader = (field: keyof FinancialEntry["accountingEntry"]["header"], nextValue: string) => {
    onChange({
      ...value,
      header: { ...value.header, [field]: nextValue },
    });
  };

  const updateLine = (
    type: AccountingLine["type"],
    lineId: string,
    field: keyof AccountingLine,
    nextValue: string | number,
  ) => {
    const key = type === "debit" ? "debitLines" : "creditLines";
    onChange({
      ...value,
      [key]: value[key].map((line) => (line.id === lineId ? { ...line, [field]: nextValue } : line)),
    });
  };

  const addLine = (type: AccountingLine["type"]) => {
    const key = type === "debit" ? "debitLines" : "creditLines";
    onChange({ ...value, [key]: [...value[key], createLine(type, currency)] });
  };

  const removeLine = (type: AccountingLine["type"], lineId: string) => {
    const key = type === "debit" ? "debitLines" : "creditLines";
    if (value[key].length <= 1) return;
    onChange({ ...value, [key]: value[key].filter((line) => line.id !== lineId) });
  };

  const renderLines = (title: string, type: AccountingLine["type"], lines: AccountingLine[]) => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{title}</p>
        <Button type="button" size="sm" variant="outline" disabled={disabled} onClick={() => addLine(type)}>
          <Plus className="h-4 w-4" /> Add line
        </Button>
      </div>

      {lines.map((line, index) => (
        <div key={line.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
          <div className="mb-3 flex items-center justify-between">
            <Badge variant={type === "debit" ? "info" : "brand"}>
              {type === "debit" ? "Debit" : "Credit"} {index + 1}
            </Badge>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              disabled={disabled || lines.length <= 1}
              onClick={() => removeLine(type, line.id)}
              aria-label={`Remove ${type} line ${index + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <Label>GL account</Label>
              <Input disabled={disabled} value={line.glAccount} onChange={(event) => updateLine(type, line.id, "glAccount", event.target.value)} />
            </div>
            <div>
              <Label>Account name</Label>
              <Input disabled={disabled} value={line.accountName} onChange={(event) => updateLine(type, line.id, "accountName", event.target.value)} />
            </div>
            <div>
              <Label>Cost center</Label>
              <Input disabled={disabled} value={line.costCenter ?? ""} onChange={(event) => updateLine(type, line.id, "costCenter", event.target.value)} />
            </div>
            <div>
              <Label>Tax code</Label>
              <Input disabled={disabled} value={line.taxCode ?? ""} onChange={(event) => updateLine(type, line.id, "taxCode", event.target.value)} />
            </div>
            <div>
              <Label>Amount</Label>
              <Input
                disabled={disabled}
                type="number"
                min="0"
                step="0.01"
                value={line.amount}
                onChange={(event) => updateLine(type, line.id, "amount", Number(event.target.value || 0))}
              />
            </div>
            <div>
              <Label>Currency</Label>
              <Input disabled={disabled} value={line.currency} onChange={(event) => updateLine(type, line.id, "currency", event.target.value.toUpperCase())} />
            </div>
            <div className="md:col-span-2">
              <Label>Memo</Label>
              <Input disabled={disabled} value={line.memo} onChange={(event) => updateLine(type, line.id, "memo", event.target.value)} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-semibold">Editable accounting entry</p>
        <p className="text-xs text-slate-500">Review header values, GL accounts, tax, cost centers, amounts, and debit/credit balance.</p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div><Label>Document type</Label><Input disabled={disabled} value={value.header.documentType} onChange={(event) => updateHeader("documentType", event.target.value)} /></div>
        <div><Label>Company code</Label><Input disabled={disabled} value={value.header.companyCode} onChange={(event) => updateHeader("companyCode", event.target.value)} /></div>
        <div><Label>Posting date</Label><Input disabled={disabled} type="date" value={value.header.postingDate} onChange={(event) => updateHeader("postingDate", event.target.value)} /></div>
        <div><Label>Document date</Label><Input disabled={disabled} type="date" value={value.header.documentDate} onChange={(event) => updateHeader("documentDate", event.target.value)} /></div>
        <div><Label>Reference</Label><Input disabled={disabled} value={value.header.reference} onChange={(event) => updateHeader("reference", event.target.value)} /></div>
        <div><Label>Header text</Label><Input disabled={disabled} value={value.header.headerText} onChange={(event) => updateHeader("headerText", event.target.value)} /></div>
      </div>

      {renderLines("Debit lines", "debit", value.debitLines)}
      {renderLines("Credit lines", "credit", value.creditLines)}

      <div className="grid gap-3 rounded-xl bg-slate-50 p-4 dark:bg-slate-900 md:grid-cols-3">
        <div><p className="text-xs text-slate-500">Debit total</p><p className="font-bold tabular">{formatCurrency(debitTotal, currency)}</p></div>
        <div><p className="text-xs text-slate-500">Credit total</p><p className="font-bold tabular">{formatCurrency(creditTotal, currency)}</p></div>
        <div><p className="text-xs text-slate-500">Balance</p><Badge variant={balanced ? "success" : "danger"}>{balanced ? "Balanced" : "Out of balance"}</Badge></div>
      </div>
    </div>
  );
}
