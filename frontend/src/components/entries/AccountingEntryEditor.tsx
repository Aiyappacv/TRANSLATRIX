import type { FinancialEntry, ValidationIssue } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ReviewAccountingEditor } from "@/components/review/ReviewAccountingEditor";

interface AccountingEntryEditorProps {
  value: FinancialEntry["accountingEntry"];
  currency: string;
  issues?: ValidationIssue[];
  disabled?: boolean;
  onChange: (value: FinancialEntry["accountingEntry"]) => void;
}

export function AccountingEntryEditor({ value, currency, issues = [], disabled, onChange }: AccountingEntryEditorProps) {
  const debitTotal = value.debitLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
  const creditTotal = value.creditLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
  const balanced = Math.abs(debitTotal - creditTotal) < 0.01;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Accounting entry editor</CardTitle>
        <CardDescription>Edit header values, add or remove debit/credit lines, and keep the journal balanced before review.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ReviewAccountingEditor value={value} currency={currency} disabled={disabled} onChange={onChange} />
        {!balanced || issues.length ? (
          <div className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
            Validation warnings: {issues.length ? issues.map((issue) => issue.message).join(" ") : "Debit and credit totals do not match."}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
