import { Tags } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { FinancialCategory } from "@/types";
import type { EntryDraft } from "@/pages/entries/FinancialEntryDetailPage";

const CATEGORIES: FinancialCategory[] = ["Expenses", "Income", "Assets", "Liabilities"];

const SUBCATEGORY_SUGGESTIONS: Record<FinancialCategory, string[]> = {
  Expenses: ["Office rent", "Cloud services", "Travel", "Utilities", "Professional fees"],
  Income: ["Professional services", "Product sales", "Subscription revenue", "Interest income"],
  Assets: ["Office equipment", "Vehicles", "Software licenses", "Prepaid expenses"],
  Liabilities: ["Accounts payable", "Accrued expenses", "Loans payable", "Deferred revenue"],
};

interface CategoryEditorProps {
  draft: EntryDraft;
  onChange: (patch: Partial<EntryDraft>) => void;
}

export function CategoryEditor({ draft, onChange }: CategoryEditorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Tags className="h-5 w-5 text-primary" />Classification &amp; entry details</CardTitle>
        <CardDescription>Correct the category, subcategory, and core financial fields extracted from the source document.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="category">Category</Label>
            <Select value={draft.category} onValueChange={(value) => onChange({ category: value as FinancialCategory, subcategory: "" })}>
              <SelectTrigger id="category"><SelectValue placeholder="Select category" /></SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((category) => <SelectItem key={category} value={category}>{category}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="subcategory">Subcategory</Label>
            <Select value={draft.subcategory} onValueChange={(value) => onChange({ subcategory: value })}>
              <SelectTrigger id="subcategory"><SelectValue placeholder="Select subcategory" /></SelectTrigger>
              <SelectContent>
                {SUBCATEGORY_SUGGESTIONS[draft.category].map((sub) => <SelectItem key={sub} value={sub}>{sub}</SelectItem>)}
                {draft.subcategory && !SUBCATEGORY_SUGGESTIONS[draft.category].includes(draft.subcategory) ? (
                  <SelectItem value={draft.subcategory}>{draft.subcategory}</SelectItem>
                ) : null}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="date">Document date</Label>
            <Input id="date" type="date" value={draft.date} onChange={(event) => onChange({ date: event.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="amount">Amount</Label>
            <Input id="amount" type="number" step="0.01" value={draft.amount} onChange={(event) => onChange({ amount: Number(event.target.value) })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="currency">Currency</Label>
            <Input id="currency" maxLength={3} className="uppercase" value={draft.currency} onChange={(event) => onChange({ currency: event.target.value.toUpperCase() })} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="vendor">Vendor</Label>
            <Input id="vendor" placeholder="Supplier name" value={draft.vendor ?? ""} onChange={(event) => onChange({ vendor: event.target.value, customer: event.target.value ? "" : draft.customer })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="customer">Customer</Label>
            <Input id="customer" placeholder="Customer name" value={draft.customer ?? ""} onChange={(event) => onChange({ customer: event.target.value, vendor: event.target.value ? "" : draft.vendor })} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="reference">Reference number</Label>
            <Input id="reference" value={draft.reference} onChange={(event) => onChange({ reference: event.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invoiceNumber">Invoice number</Label>
            <Input id="invoiceNumber" value={draft.invoiceNumber ?? ""} onChange={(event) => onChange({ invoiceNumber: event.target.value })} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
