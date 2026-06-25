import { useQuery } from "@tanstack/react-query";
import { Database, FileStack, ScanText } from "lucide-react";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { PlatformUsageChart } from "@/components/super-admin/PlatformUsageChart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { formatNumber } from "@/utils/formatters";
import { downloadCsv } from "@/utils/downloads";

export function SuperAdminUsageAnalyticsPage() {
  const dashboard = useQuery({ queryKey: ["super-admin", "usage-dashboard"], queryFn: superAdminApi.getDashboard });
  const companies = useQuery({ queryKey: ["super-admin", "usage-companies"], queryFn: superAdminApi.getCompanies });
  if (dashboard.isLoading || companies.isLoading) return <LoadingState label="Loading usage analytics..." />;
  const kpis = dashboard.data?.kpis ?? [];
  const value = (key: string) => kpis.find((kpi) => kpi.key === key)?.value ?? 0;
  const maxEntries = Math.max(...(companies.data ?? []).map((company) => company.entriesProcessed), 1);
  const exportUsage = () => downloadCsv(
    `translatrix-platform-usage-${new Date().toISOString().slice(0, 10)}.csv`,
    ["Company", "Tenant ID", "Plan", "Status", "Files", "Entries", "SAP postings", "Accounting postings", "Storage GB"],
    (companies.data ?? []).map((company) => [company.companyName, company.tenantId, company.plan, company.status, company.filesProcessed, company.entriesProcessed, company.sapPostings, company.accountingPostings, company.storageUsedGb]),
  );
  return (
    <>
      <PageHeader eyebrow="Platform metering" title="Usage analytics" description="Track billable and capacity-driving consumption across OCR, storage, files, entries, and accounting postings." actions={<Button variant="outline" onClick={exportUsage} disabled={!(companies.data ?? []).length}>Export usage CSV</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Files processed" value={formatNumber(value("files_processed"))} icon={FileStack} />
        <MetricCard label="OCR pages" value={formatNumber(value("ocr_usage"))} tone="info" icon={ScanText} />
        <MetricCard label="Storage used" value={`${formatNumber(value("storage_used"))} GB`} tone="warning" icon={Database} />
      </div>
      <Card>
        <CardHeader><CardTitle>Usage trend</CardTitle><CardDescription>Seven-day volume trend across the platform.</CardDescription></CardHeader>
        <CardContent><PlatformUsageChart data={dashboard.data?.usageTrend ?? []} /></CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader><CardTitle>Tenant consumption distribution</CardTitle><CardDescription>Entry volume compared with the highest-volume tenant.</CardDescription></CardHeader>
        <CardContent className="space-y-5">
          {(companies.data ?? []).map((company) => (
            <div key={company.id}>
              <div className="mb-2 flex items-center justify-between gap-4 text-sm"><span className="font-semibold">{company.companyName}</span><span className="text-slate-500">{formatNumber(company.entriesProcessed)} entries · {company.storageUsedGb} GB</span></div>
              <Progress value={(company.entriesProcessed / maxEntries) * 100} />
            </div>
          ))}
        </CardContent>
      </Card>
    </>
  );
}
