import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { monitoringApi } from "@/services/monitoringApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { ErrorGroupCard } from "@/components/common/ErrorGroupCard";
import { MetricCard } from "@/components/common/MetricCard";
import { useToast } from "@/hooks/useToast";

const labels = { ocr: "OCR errors", translation: "Translation errors", validation: "Validation errors", sap_posting: "SAP posting errors", integration: "Integration errors" } as const;

export function ErrorCenterPage() {
  const toast = useToast(); const client = useQueryClient();
  const query = useQuery({ queryKey: ["monitoring", "errors"], queryFn: monitoringApi.getErrors });
  const retry = useMutation({ mutationFn: monitoringApi.retryError, onSuccess: () => { client.invalidateQueries({ queryKey: ["monitoring", "errors"] }); toast.success("Retry queued", "The operation will preserve its idempotency key."); }, onError: (error) => toast.error("Retry failed", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading error center..." />;
  if (query.isError) return <ErrorState title="Error center unavailable" description="Operational errors could not be loaded." onRetry={() => query.refetch()} />;
  const errors = query.data ?? []; const retryable = errors.filter((error) => error.retryable).length; const critical = errors.filter((error) => error.severity === "critical").length;
  return <div className="space-y-6"><PageHeader eyebrow="Phase 13 · Monitoring" title="Error center" description="Grouped OCR, translation, validation, SAP posting, and integration errors with retryability controls." />
    <div className="grid gap-4 md:grid-cols-3"><MetricCard label="Open errors" value={String(errors.length)} delta="Across all processing stages" tone="warning" /><MetricCard label="Retryable" value={String(retryable)} delta="Safe automated retry" tone="info" /><MetricCard label="Critical" value={String(critical)} delta="Manual remediation required" tone={critical ? "danger" : "success"} /></div>
    {Object.entries(labels).map(([category, title]) => <ErrorGroupCard key={category} title={title} errors={errors.filter((error) => error.category === category)} pendingId={retry.isPending ? retry.variables : undefined} onRetry={(id) => retry.mutate(id)} />)}
  </div>;
}
