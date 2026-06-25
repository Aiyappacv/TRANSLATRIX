import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { entryApi } from "@/services/entryApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { FinancialEntryTable } from "@/components/entries/FinancialEntryTable";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ValidationIssuesPage() {
  const query = useQuery({ queryKey: ["entries", "validation-issues"], queryFn: entryApi.getValidationIssues });
  const entries = query.data ?? [];
  const errorCount = entries.reduce((sum, entry) => sum + entry.issues.filter((issue) => issue.severity === "error").length, 0);
  const warningCount = entries.reduce((sum, entry) => sum + entry.issues.filter((issue) => issue.severity === "warning").length, 0);
  return (
    <>
      <PageHeader eyebrow="Processing" title="Validation issues" description="Entries with failed or warning validation status before review and posting." />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Issue entries" value={String(entries.length)} tone="warning" icon={ShieldAlert} />
        <MetricCard label="Errors" value={String(errorCount)} tone={errorCount ? "danger" : "success"} icon={AlertTriangle} />
        <MetricCard label="Warnings" value={String(warningCount)} tone={warningCount ? "warning" : "success"} icon={AlertTriangle} />
      </div>
      <Card><CardHeader><CardTitle>Entries requiring correction</CardTitle><CardDescription>Open an entry to fix category, tax code, GL account, SAP T-Code mapping, or debit-credit balance.</CardDescription></CardHeader><CardContent>{query.isLoading ? <LoadingState /> : <FinancialEntryTable entries={entries} />}</CardContent></Card>
    </>
  );
}
