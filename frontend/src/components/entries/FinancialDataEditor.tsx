import type { FinancialEntry } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function FinancialDataEditor({ entry }: { entry: FinancialEntry }) {
  const fields = [
    ["Date", entry.date],
    ["Amount", String(entry.amount)],
    ["Currency", entry.currency],
    ["Vendor", entry.vendor ?? ""],
    ["Customer", entry.customer ?? ""],
    ["Reference number", entry.referenceNumber],
    ["Invoice number", entry.invoiceNumber ?? ""],
    ["GL account", entry.glAccount],
    ["Cost center", entry.costCenter ?? ""],
    ["Tax code", entry.taxCode ?? ""],
    ["SAP T-Code", entry.sapTCode],
    ["Posting process", entry.postingProcess],
  ];
  return (
    <Card>
      <CardHeader><CardTitle>Editable financial data</CardTitle><CardDescription>Category, date, amount, party, references, GL account, cost center, tax code, SAP T-Code, and posting process are represented for editing.</CardDescription></CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        {fields.map(([label, value]) => <div key={label} className="space-y-2"><Label>{label}</Label><Input value={value} readOnly /></div>)}
      </CardContent>
    </Card>
  );
}
