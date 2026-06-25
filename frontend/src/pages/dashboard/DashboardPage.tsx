import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Clock3, FileCheck2, PercentCircle } from "lucide-react";
import { analyticsApi } from "@/services/analyticsApi";
import { useAuthStore } from "@/store/authStore";
import { roleLabels } from "@/utils/permissions";
import { entryApi } from "@/services/entryApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ProcessingTrendChart } from "@/components/dashboard/ProcessingTrendChart";
import { ClassificationSplitChart } from "@/components/dashboard/ClassificationSplitChart";
import { FinancialEntryTable } from "@/components/entries/FinancialEntryTable";

const icons = [FileCheck2, Clock3, PercentCircle, AlertTriangle];

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const role = user?.roles?.[0];
  const summary = useQuery({ queryKey: ["analytics", "summary"], queryFn: analyticsApi.getSummary });
  const entries = useQuery({ queryKey: ["entries"], queryFn: entryApi.getEntries });

  if (summary.isLoading) return <LoadingState />;
  if (summary.isError || !summary.data) return <ErrorState description="Analytics summary could not be loaded" onRetry={() => summary.refetch()} />;

  return (
    <>
      <PageHeader
        eyebrow="Operations overview"
        title={user?.isPlatformOwner ? "SPECTRA AI platform cockpit" : `${user?.companyName ?? "Company"} finance cockpit`}
        description={user?.isPlatformOwner ? "Monitor registered client companies, usage, workflows, and audit visibility across the product." : `Logged in as ${role ? roleLabels[role] : "user"}. Monitor ingestion, OCR extraction, translation, classification, approval, and posting for this company.`}
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summary.data.kpis.map((kpi, index) => <MetricCard key={kpi.label} {...kpi} icon={icons[index]} />)}
      </div>
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Processing trend</CardTitle><CardDescription>Files, entries, posted transactions, and failed items over the last week.</CardDescription></CardHeader>
          <CardContent><ProcessingTrendChart data={summary.data.processingTrend} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Classification split</CardTitle><CardDescription>Expenses, Income, Assets, and Liabilities distribution.</CardDescription></CardHeader>
          <CardContent><ClassificationSplitChart data={summary.data.classificationSplit} /></CardContent>
        </Card>
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Priority review queue</CardTitle><CardDescription>Entries requiring human review before accounting posting.</CardDescription></CardHeader>
        <CardContent>{entries.isLoading ? <LoadingState label="Loading entries..." /> : <FinancialEntryTable entries={(entries.data ?? []).filter((entry) => entry.status !== "sap_posted")} />}</CardContent>
      </Card>
    </>
  );
}
