import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, TestTube2 } from "lucide-react";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { ProviderStatusCard } from "@/components/super-admin/ProviderStatusCard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/useToast";

export function SuperAdminIntegrationsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const providers = useQuery({ queryKey: ["super-admin", "providers"], queryFn: superAdminApi.getProviders });
  const test = useMutation({
    mutationFn: superAdminApi.testProvider,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "providers"] });
      toast.success("Provider test completed", `${result.providerCode} reported ${result.status}.`);
    },
  });
  if (providers.isLoading) return <LoadingState label="Loading provider health..." />;
  const data = providers.data ?? [];
  return (
    <>
      <PageHeader eyebrow="Provider operations" title="Integration monitoring" description="Monitor PaddleOCR, cloud OCR, translation providers, SAP, QuickBooks, Xero, Zoho, Tally, Sage, and NetSuite from one extensible provider registry." actions={<Button variant="outline" onClick={() => providers.refetch()}><RefreshCw className="h-4 w-4" />Refresh</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Providers" value={String(data.length)} />
        <MetricCard label="Operational" value={String(data.filter((provider) => provider.status === "operational").length)} tone="success" />
        <MetricCard label="Degraded" value={String(data.filter((provider) => provider.status === "degraded").length)} tone="warning" />
        <MetricCard label="Open incidents" value={String(data.reduce((sum, provider) => sum + provider.incidentsOpen, 0))} tone="danger" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.map((provider) => (
          <div key={provider.code} className="space-y-2">
            <ProviderStatusCard provider={provider} />
            <Card><CardContent className="flex items-center justify-between p-3"><span className="text-xs text-slate-500">{provider.environment}</span><Button variant="outline" size="sm" disabled={test.isPending} onClick={() => test.mutate(provider.code)}><TestTube2 className="h-4 w-4" />Test provider</Button></CardContent></Card>
          </div>
        ))}
      </div>
    </>
  );
}
