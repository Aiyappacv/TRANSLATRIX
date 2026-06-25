import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheckBig, Clock3, Layers3, PauseCircle, PlayCircle, RotateCcw, TriangleAlert } from "lucide-react";
import type { JobQueueMetric } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { DataTable } from "@/components/common/DataTable";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { useToast } from "@/hooks/useToast";
import { formatNumber } from "@/utils/formatters";

export function SuperAdminJobQueuesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [paused, setPaused] = useState(false);
  const queues = useQuery({ queryKey: ["super-admin", "queues"], queryFn: superAdminApi.getJobQueues });
  const retry = useMutation({
    mutationFn: superAdminApi.retryFailedQueueJobs,
    onSuccess: async (queue) => {
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "queues"] });
      toast.success("Failed jobs retried", `${queue.name} now has ${queue.failed} failed jobs and ${queue.waiting} waiting jobs.`);
    },
    onError: (error) => toast.error("Retry failed", error instanceof Error ? error.message : "Unable to retry queue jobs."),
  });
  const pause = useMutation({
    mutationFn: superAdminApi.setNonCriticalQueuesPaused,
    onSuccess: async (result) => {
      setPaused(result.paused);
      queryClient.setQueryData(["super-admin", "queues"], result.queues);
      toast.success(result.paused ? "Non-critical queues paused" : "Non-critical queues resumed", "Ingestion and classification queue state was updated and audited.");
    },
    onError: (error) => toast.error("Queue update failed", error instanceof Error ? error.message : "Unable to update queues."),
  });
  const columns = useMemo<ColumnDef<JobQueueMetric>[]>(() => [
    { accessorKey: "name", header: "Queue" },
    { accessorKey: "type", header: "Workflow" },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <PlatformStatusBadge status={row.original.status} /> },
    { accessorKey: "waiting", header: "Waiting" },
    { accessorKey: "active", header: "Active" },
    { accessorKey: "failed", header: "Failed" },
    { accessorKey: "completed24h", header: "Completed (24h)", cell: ({ row }) => formatNumber(row.original.completed24h) },
    { accessorKey: "oldestJobAgeSeconds", header: "Oldest job", cell: ({ row }) => `${row.original.oldestJobAgeSeconds}s` },
    { accessorKey: "throughputPerMinute", header: "Throughput/min" },
    { id: "actions", header: "Actions", cell: ({ row }) => <Button variant="outline" size="sm" disabled={row.original.failed === 0 || retry.isPending} onClick={() => retry.mutate(row.original.id)}><RotateCcw className="h-4 w-4" />{retry.isPending && retry.variables === row.original.id ? "Retrying..." : "Retry failed"}</Button> },
  ], [retry]);
  if (queues.isLoading) return <LoadingState label="Loading job queues..." />;
  const data = queues.data ?? [];
  return (
    <>
      <PageHeader eyebrow="Workflow infrastructure" title="Job queues" description="Monitor backlog, active workers, failed jobs, oldest job age, and throughput across every processing stage." actions={<ConfirmDialog destructive={false} title={paused ? "Resume non-critical queues?" : "Pause non-critical queues?"} description={paused ? "Ingestion and classification jobs will resume processing." : "Ingestion and classification jobs will stop accepting active work until resumed. Review and posting remain available."} confirmLabel={paused ? "Resume queues" : "Pause queues"} onConfirm={async () => { await pause.mutateAsync(!paused); }} trigger={<Button variant="outline" disabled={pause.isPending}>{paused ? <PlayCircle className="h-4 w-4" /> : <PauseCircle className="h-4 w-4" />}{paused ? "Resume non-critical queues" : "Pause non-critical queues"}</Button>} />} />
      <div className="mb-6 grid gap-4 md:grid-cols-4"><MetricCard label="Total waiting" value={formatNumber(data.reduce((sum, queue) => sum + queue.waiting, 0))} tone="warning" icon={Layers3} /><MetricCard label="Active workers" value={formatNumber(data.reduce((sum, queue) => sum + queue.active, 0))} tone="info" icon={Clock3} /><MetricCard label="Failed jobs" value={formatNumber(data.reduce((sum, queue) => sum + queue.failed, 0))} tone="danger" icon={TriangleAlert} /><MetricCard label="Completed (24h)" value={formatNumber(data.reduce((sum, queue) => sum + queue.completed24h, 0))} tone="success" icon={CircleCheckBig} /></div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search queues and workflow types..." exportFileName="platform-job-queues" /></CardContent></Card>
    </>
  );
}
