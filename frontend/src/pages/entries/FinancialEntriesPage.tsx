import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Filter, ListChecks, SlidersHorizontal } from "lucide-react";
import type { FinancialCategory, FinancialEntry } from "@/types";
import { entryApi } from "@/services/entryApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { FinancialEntryTable } from "@/components/entries/FinancialEntryTable";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function matchesRange(value: number, min: string, max: string) {
  const parsedMin = min ? Number(min) : Number.NEGATIVE_INFINITY;
  const parsedMax = max ? Number(max) : Number.POSITIVE_INFINITY;
  return value >= parsedMin && value <= parsedMax;
}

export function FinancialEntriesPage() {
  const query = useQuery({ queryKey: ["entries"], queryFn: entryApi.getEntries });
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [currency, setCurrency] = useState("all");
  const [sapTCode, setSapTCode] = useState("");
  const [sourceBatch, setSourceBatch] = useState("");
  const [validationStatus, setValidationStatus] = useState("all");
  const [confidenceMin, setConfidenceMin] = useState("");
  const [confidenceMax, setConfidenceMax] = useState("");
  const [amountMin, setAmountMin] = useState("");
  const [amountMax, setAmountMax] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const entries = useMemo(() => query.data ?? [], [query.data]);
  const categories: FinancialCategory[] = ["Expenses", "Income", "Assets", "Liabilities"];
  const currencies = Array.from(new Set(entries.map((entry) => entry.currency)));

  const filtered = useMemo(() => entries.filter((entry: FinancialEntry) => {
    if (category !== "all" && entry.category !== category) return false;
    if (status !== "all" && entry.status !== status) return false;
    if (currency !== "all" && entry.currency !== currency) return false;
    if (validationStatus !== "all" && entry.validationStatus !== validationStatus) return false;
    if (sapTCode && !entry.sapTCode.toLowerCase().includes(sapTCode.toLowerCase())) return false;
    if (sourceBatch && !entry.sourceBatch.toLowerCase().includes(sourceBatch.toLowerCase())) return false;
    if (!matchesRange(entry.confidence.overall, confidenceMin ? String(Number(confidenceMin) / 100) : "", confidenceMax ? String(Number(confidenceMax) / 100) : "")) return false;
    if (!matchesRange(entry.amount, amountMin, amountMax)) return false;
    if (dateFrom && entry.date < dateFrom) return false;
    if (dateTo && entry.date > dateTo) return false;
    return true;
  }), [entries, category, status, currency, validationStatus, sapTCode, sourceBatch, confidenceMin, confidenceMax, amountMin, amountMax, dateFrom, dateTo]);

  const needsReview = entries.filter((entry) => entry.status === "needs_review").length;
  const failed = entries.filter((entry) => entry.validationStatus === "failed").length;
  const totalAmount = entries.reduce((sum, entry) => sum + entry.amount, 0);

  return (
    <>
      <PageHeader eyebrow="Processing" title="Financial entries" description="Core finance workflow where extracted data becomes reviewed accounting entries with classification, SAP T-Code mapping, validation, and accounting editor controls." />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Entries" value={String(entries.length)} tone="info" icon={ListChecks} />
        <MetricCard label="Needs review" value={String(needsReview)} tone="warning" icon={SlidersHorizontal} />
        <MetricCard label="Validation failed" value={String(failed)} tone={failed ? "danger" : "success"} icon={Filter} />
        <MetricCard label="Total amount records" value={String(Math.round(totalAmount))} tone="neutral" icon={Download} />
      </div>
      <Card className="mb-6">
        <CardHeader><CardTitle>Filters</CardTitle><CardDescription>Category, status, confidence range, source batch, amount range, currency, date range, SAP T-Code, and validation status.</CardDescription></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="space-y-2"><Label>Category</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={category} onChange={(e) => setCategory(e.target.value)}><option value="all">All</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></div>
          <div className="space-y-2"><Label>Status</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All</option>{["needs_review", "validation_failed", "approved", "sap_posted", "sap_failed", "processing"].map((item) => <option key={item} value={item}>{item}</option>)}</select></div>
          <div className="space-y-2"><Label>Currency</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={currency} onChange={(e) => setCurrency(e.target.value)}><option value="all">All</option>{currencies.map((item) => <option key={item} value={item}>{item}</option>)}</select></div>
          <div className="space-y-2"><Label>Validation status</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={validationStatus} onChange={(e) => setValidationStatus(e.target.value)}><option value="all">All</option><option value="valid">Valid</option><option value="warning">Warning</option><option value="failed">Failed</option></select></div>
          <div className="space-y-2"><Label>Confidence min %</Label><Input value={confidenceMin} onChange={(e) => setConfidenceMin(e.target.value)} placeholder="80" /></div>
          <div className="space-y-2"><Label>Confidence max %</Label><Input value={confidenceMax} onChange={(e) => setConfidenceMax(e.target.value)} placeholder="100" /></div>
          <div className="space-y-2"><Label>Source batch</Label><Input value={sourceBatch} onChange={(e) => setSourceBatch(e.target.value)} placeholder="batch_..." /></div>
          <div className="space-y-2"><Label>SAP T-Code</Label><Input value={sapTCode} onChange={(e) => setSapTCode(e.target.value)} placeholder="FB60" /></div>
          <div className="space-y-2"><Label>Amount min</Label><Input value={amountMin} onChange={(e) => setAmountMin(e.target.value)} /></div>
          <div className="space-y-2"><Label>Amount max</Label><Input value={amountMax} onChange={(e) => setAmountMax(e.target.value)} /></div>
          <div className="space-y-2"><Label>Date from</Label><Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></div>
          <div className="space-y-2"><Label>Date to</Label><Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></div>
        </CardContent>
      </Card>
      {query.isLoading ? <LoadingState /> : <FinancialEntryTable entries={filtered} />}
    </>
  );
}
