import { Filter, RotateCcw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { FinancialCategory, EntryStatus } from "@/types";

export interface EntryFilterState {
  category: FinancialCategory | "all";
  status: EntryStatus | "all";
  minConfidence: string;
  maxConfidence: string;
  sourceBatch: string;
  minAmount: string;
  maxAmount: string;
  currency: string;
  dateFrom: string;
  dateTo: string;
  sapTCode: string;
  validationStatus: "all" | "issues" | "clean";
}

export const defaultEntryFilters: EntryFilterState = {
  category: "all",
  status: "all",
  minConfidence: "",
  maxConfidence: "",
  sourceBatch: "all",
  minAmount: "",
  maxAmount: "",
  currency: "all",
  dateFrom: "",
  dateTo: "",
  sapTCode: "all",
  validationStatus: "all",
};

interface EntryFiltersProps {
  filters: EntryFilterState;
  onChange: (patch: Partial<EntryFilterState>) => void;
  onReset: () => void;
  batches: string[];
  currencies: string[];
  sapTCodes: string[];
  statuses: EntryStatus[];
}

const CATEGORIES: FinancialCategory[] = ["Expenses", "Income", "Assets", "Liabilities"];

export function EntryFilters({ filters, onChange, onReset, batches, currencies, sapTCodes, statuses }: EntryFiltersProps) {
  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><Filter className="h-4 w-4 text-primary" />Filters</p>
          <Button variant="ghost" size="sm" onClick={onReset}><RotateCcw className="h-3.5 w-3.5" />Reset</Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Category</Label>
            <Select value={filters.category} onValueChange={(value) => onChange({ category: value as EntryFilterState["category"] })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORIES.map((category) => <SelectItem key={category} value={category}>{category}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Status</Label>
            <Select value={filters.status} onValueChange={(value) => onChange({ status: value as EntryFilterState["status"] })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {statuses.map((status) => <SelectItem key={status} value={status}>{status.replaceAll("_", " ")}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Source batch</Label>
            <Select value={filters.sourceBatch} onValueChange={(value) => onChange({ sourceBatch: value })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All batches</SelectItem>
                {batches.map((batch) => <SelectItem key={batch} value={batch}>{batch}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">SAP T-Code</Label>
            <Select value={filters.sapTCode} onValueChange={(value) => onChange({ sapTCode: value })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All T-Codes</SelectItem>
                {sapTCodes.map((code) => <SelectItem key={code} value={code}>{code}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Currency</Label>
            <Select value={filters.currency} onValueChange={(value) => onChange({ currency: value })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All currencies</SelectItem>
                {currencies.map((currency) => <SelectItem key={currency} value={currency}>{currency}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Validation status</Label>
            <Select value={filters.validationStatus} onValueChange={(value) => onChange({ validationStatus: value as EntryFilterState["validationStatus"] })}>
              <SelectTrigger className="h-9 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All entries</SelectItem>
                <SelectItem value="issues">Has validation issues</SelectItem>
                <SelectItem value="clean">No issues</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Confidence range</Label>
            <div className="flex items-center gap-2">
              <Input className="h-9 text-sm" type="number" min={0} max={100} placeholder="Min %" value={filters.minConfidence} onChange={(event) => onChange({ minConfidence: event.target.value })} />
              <span className="text-xs text-slate-400">to</span>
              <Input className="h-9 text-sm" type="number" min={0} max={100} placeholder="Max %" value={filters.maxConfidence} onChange={(event) => onChange({ maxConfidence: event.target.value })} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Amount range</Label>
            <div className="flex items-center gap-2">
              <Input className="h-9 text-sm" type="number" placeholder="Min" value={filters.minAmount} onChange={(event) => onChange({ minAmount: event.target.value })} />
              <span className="text-xs text-slate-400">to</span>
              <Input className="h-9 text-sm" type="number" placeholder="Max" value={filters.maxAmount} onChange={(event) => onChange({ maxAmount: event.target.value })} />
            </div>
          </div>

          <div className="space-y-1.5 sm:col-span-2 lg:col-span-2">
            <Label className="text-xs">Date range</Label>
            <div className="flex items-center gap-2">
              <Input className="h-9 text-sm" type="date" value={filters.dateFrom} onChange={(event) => onChange({ dateFrom: event.target.value })} />
              <span className="text-xs text-slate-400">to</span>
              <Input className="h-9 text-sm" type="date" value={filters.dateTo} onChange={(event) => onChange({ dateTo: event.target.value })} />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
