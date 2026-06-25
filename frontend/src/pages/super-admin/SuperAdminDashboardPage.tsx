import { useQuery } from "@tanstack/react-query";
import { Activity, Building2, Database, FileStack, Gauge, Layers3, ReceiptText, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PlatformUsageChart } from "@/components/super-admin/PlatformUsageChart";
import { ProviderStatusCard } from "@/components/super-admin/ProviderStatusCard";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { formatCurrency, formatNumber } from "@/utils/formatters";

const icons = [Building2, Building2, Building2, Building2, UsersRound, FileStack, ReceiptText, ReceiptText, ReceiptText, FileStack, Gauge, Activity, Activity, ReceiptText, Database, Layers3, Gauge];

function formatKpi(value: number, unit?: string) {
  if (unit === "percent") return `${value}%`;
  if (unit === "currency") return formatCurrency(value, "USD");
  if (unit === "storage") return `${formatNumber(value)} GB`;
  return formatNumber(value);
}

export function SuperAdminDashboardPage() {
  const dashboard = useQuery({ queryKey: ["super-admin", "dashboard"], queryFn: superAdminApi.getDashboard, refetchInterval: 20000, refetchIntervalInBackground: false });
  const providers = useQuery({ queryKey: ["super-admin", "providers"], queryFn: superAdminApi.getProviders, refetchInterval: 20000, refetchIntervalInBackground: false });
  const queues = useQuery({ queryKey: ["super-admin", "queues"], queryFn: superAdminApi.getJobQueues, refetchInterval: 20000, refetchIntervalInBackground: false });

  if (dashboard.isLoading || providers.isLoading || queues.isLoading) return <LoadingState label="Loading platform operations..." />;
  if (dashboard.isError || !dashboard.data) return <ErrorState description="Platform dashboard could not be loaded." onRetry={() => dashboard.refetch()} />;

  return (
    <>
      <PageHeader
        eyebrow="SPECTRA AI platform control plane"
        title="Super Admin dashboard"
        description="Monitor every tenant, provider, usage meter, posting channel, queue, and platform reliability objective from a separately governed administration workspace."
        badge="Production"
        actions={<><Button asChild variant="outline"><Link to="/super-admin/system-health">System health</Link></Button><Button asChild><Link to="/super-admin/company-onboarding">Onboard company</Link></Button></>}
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dashboard.data.kpis.map((kpi, index) => <MetricCard key={kpi.key} label={kpi.label} value={formatKpi(kpi.value, kpi.unit)} delta={kpi.delta} tone={kpi.tone} icon={icons[index]} />)}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <Card>
          <CardHeader><CardTitle>Seven-day platform throughput</CardTitle><CardDescription>Daily files, financial entries, and downstream accounting postings across all tenants.</CardDescription></CardHeader>
          <CardContent><PlatformUsageChart data={dashboard.data.usageTrend} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Top tenant consumption</CardTitle><CardDescription>Highest-volume companies for capacity and commercial planning.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {dashboard.data.topCompanies.map((company) => (
              <Link key={company.companyId} to={`/super-admin/companies/${company.companyId}`} className="block rounded-2xl border border-slate-200 p-4 transition hover:border-primary/40 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900">
                <p className="font-semibold">{company.companyName}</p>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500"><span>{formatNumber(company.filesProcessed)} files</span><span>{formatNumber(company.entriesProcessed)} entries</span><span>{company.storageUsedGb} GB</span></div>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_0.7fr]">
        <div>
          <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Provider monitoring</h2><Button asChild variant="ghost" size="sm"><Link to="/super-admin/integrations">View all providers</Link></Button></div>
          <div className="grid gap-4 md:grid-cols-2">{(providers.data ?? []).slice(0, 4).map((provider) => <ProviderStatusCard key={provider.code} provider={provider} />)}</div>
        </div>
        <Card>
          <CardHeader><CardTitle>Job queue posture</CardTitle><CardDescription>Live backlog and failure posture by workflow stage.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {(queues.data ?? []).map((queue) => (
              <div key={queue.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                <div><p className="text-sm font-semibold">{queue.name}</p><p className="mt-1 text-xs text-slate-500">{queue.waiting} waiting · {queue.active} active · {queue.failed} failed</p></div>
                <PlatformStatusBadge status={queue.status} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
