import type { ColumnDef } from "@tanstack/react-table";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock3, FileSearch, Link2, PlayCircle, RefreshCcw, ShieldCheck } from "lucide-react";
import type { FileDiscoveryItem } from "@/types";
import { ingestionApi } from "@/services/ingestionApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatNumber } from "@/utils/formatters";
import { ErrorState } from "@/components/common/ErrorState";
import { useToast } from "@/hooks/useToast";

const fileColumns: ColumnDef<FileDiscoveryItem>[] = [
  { accessorKey: "fileName", header: "File", cell: ({ row }) => <div><p className="font-semibold">{row.original.fileName}</p><p className="text-xs text-slate-500">{row.original.path}</p></div> },
  { accessorKey: "mimeType", header: "Type" },
  { accessorKey: "sizeBytes", header: "Size", cell: ({ row }) => `${formatNumber(row.original.sizeBytes / 1024)} KB` },
  { accessorKey: "status", header: "Status", cell: ({ row }) => row.original.status === "supported" ? <Badge variant="success">Supported</Badge> : <Badge variant="warning">{row.original.status}</Badge> },
  { accessorKey: "reason", header: "Reason", cell: ({ row }) => row.original.reason ?? "Ready for processing" },
  { accessorKey: "discoveredAt", header: "Discovered", cell: ({ row }) => formatDateTime(row.original.discoveredAt) },
];

export function SharedLinkDetailPage() {
  const { linkId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const query = useQuery({ queryKey: ["shared-link", linkId], queryFn: () => ingestionApi.getSharedLink(linkId), enabled: Boolean(linkId) });
  const refreshQueries = async () => Promise.all([queryClient.invalidateQueries({ queryKey: ["shared-link", linkId] }), queryClient.invalidateQueries({ queryKey: ["shared-links"] })]);
  const revalidate = useMutation({ mutationFn: () => ingestionApi.revalidateSharedLink(linkId), onSuccess: async () => { await refreshQueries(); toast.success("Source revalidated", "File discovery results were refreshed."); }, onError: (error) => toast.error("Revalidation failed", error instanceof Error ? error.message : "Unknown error") });
  const sync = useMutation({ mutationFn: () => ingestionApi.syncSharedLink(linkId), onSuccess: async () => { await refreshQueries(); toast.success("Source synchronized"); }, onError: (error) => toast.error("Synchronization failed", error instanceof Error ? error.message : "Unknown error") });
  const createBatch = useMutation({
    mutationFn: () => ingestionApi.createBatchFromSource(linkId),
    onSuccess: async (result) => {
      await Promise.all([queryClient.invalidateQueries({ queryKey: ["batches"] }), queryClient.invalidateQueries({ queryKey: ["files"] }), queryClient.invalidateQueries({ queryKey: ["entries"] }), queryClient.invalidateQueries({ queryKey: ["review-tasks"] })]);
      toast.success("Batch created", "Discovered files were attached and processed.");
      navigate(`/app/ingestion/batches/${result.batchId}`);
    },
    onError: (error) => toast.error("Batch creation failed", error instanceof Error ? error.message : "Unknown error"),
  });

  if (query.isLoading) return <LoadingState />;
  if (query.isError || !query.data) return <ErrorState description="Shared link detail could not be loaded" onRetry={() => query.refetch()} />;
  const source = query.data;
  const validation = source.validation;
  const canCreateBatch = validation.accessible && validation.supportedFilesCount > 0;

  return (
    <>
      <PageHeader
        eyebrow="Shared link detail"
        title={source.name}
        badge={source.sourceType}
        description={`${source.clientName} · ${source.folderPath || source.url} · Last sync ${formatDateTime(source.lastSyncAt)}`}
        actions={<><Button asChild variant="outline"><Link to="/app/ingestion/shared-links">Back</Link></Button><Button variant="outline" disabled={revalidate.isPending} onClick={() => revalidate.mutate()}><RefreshCcw className={`h-4 w-4 ${revalidate.isPending ? "animate-spin" : ""}`} />Revalidate</Button><Button variant="outline" disabled={sync.isPending} onClick={() => sync.mutate()}><RefreshCcw className={`h-4 w-4 ${sync.isPending ? "animate-spin" : ""}`} />Sync now</Button><Button disabled={createBatch.isPending || !canCreateBatch} onClick={() => createBatch.mutate()} title={!canCreateBatch ? "Discover at least one supported file before creating a batch" : undefined}><PlayCircle className="h-4 w-4" />{createBatch.isPending ? "Creating batch..." : "Create processing batch"}</Button></>}
      />

      {!canCreateBatch ? <div className="mb-6 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 text-warning" /><div><p className="font-semibold">No supported files are ready for batching</p><p className="mt-1 text-slate-600 dark:text-slate-300">Use Revalidate or Sync now. Private Google Drive, OneDrive, SharePoint, Dropbox, S3, Azure Blob, and SFTP sources require provider credentials; public URLs and Local Upload discovery work without external credentials.</p></div></div></div> : null}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard label="Files found" value={String(validation.filesFound)} tone="info" icon={FileSearch} />
        <MetricCard label="Supported" value={String(validation.supportedFilesCount)} tone="success" icon={CheckCircle2} />
        <MetricCard label="Unsupported" value={String(validation.unsupportedFilesCount)} tone={validation.unsupportedFilesCount ? "warning" : "success"} icon={AlertTriangle} />
        <MetricCard label="Estimated processing" value={validation.estimatedProcessingTime} tone="neutral" icon={Clock3} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><Link2 className="h-5 w-5 text-primary" />Source settings</CardTitle><CardDescription>Defaults applied when a processing batch is created.</CardDescription></CardHeader><CardContent><dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div><dt className="text-slate-500">Status</dt><dd className="mt-1"><StatusBadge status={source.status === "active" ? "completed" : source.status === "failed" ? "sap_failed" : "draft"} /></dd></div>
          <div><dt className="text-slate-500">Authentication</dt><dd className="mt-1 font-medium">{source.authenticationType}</dd></div>
          <div><dt className="text-slate-500">Schedule mode</dt><dd className="mt-1 font-medium">{source.schedule}</dd></div>
          <div><dt className="text-slate-500">Allowed domain</dt><dd className="mt-1 font-medium">{source.allowedDomain || "Not restricted"}</dd></div>
          <div><dt className="text-slate-500">File filters</dt><dd className="mt-1 font-medium">{source.fileFilters}</dd></div>
          <div><dt className="text-slate-500">Company code</dt><dd className="mt-1 font-medium">{source.defaultCompanyCode}</dd></div>
          <div><dt className="text-slate-500">Currency</dt><dd className="mt-1 font-medium">{source.defaultCurrency}</dd></div>
          <div><dt className="text-slate-500">Reviewer group</dt><dd className="mt-1 font-medium">{source.defaultReviewerGroup}</dd></div>
          <div className="sm:col-span-2"><dt className="text-slate-500">Accounting integration</dt><dd className="mt-1 font-medium">{source.defaultAccountingIntegration}</dd></div>
        </dl></CardContent></Card>

        <Card><CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" />Validation result</CardTitle><CardDescription>Connectivity, discovery, and security result.</CardDescription></CardHeader><CardContent className="space-y-4">
          <div className={`rounded-2xl border p-4 ${validation.accessible ? "border-success/30 bg-success/10" : "border-danger/30 bg-danger/10"}`}><div className="flex items-center gap-3">{validation.accessible ? <CheckCircle2 className="h-5 w-5 text-success" /> : <AlertTriangle className="h-5 w-5 text-danger" />}<div><p className="font-semibold">{validation.accessible ? "Accessible" : "Not accessible"}</p><p className="text-xs text-slate-500">Validation latency {validation.latencyMs}ms</p></div></div></div>
          {validation.securityWarning ? <div className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning"><div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4" /><span>{validation.securityWarning}</span></div></div> : <div className="rounded-2xl border border-success/30 bg-success/10 p-4 text-sm text-success">No security warning detected.</div>}
        </CardContent></Card>
      </div>

      <Card className="mt-6"><CardHeader><CardTitle>File discovery table</CardTitle><CardDescription>Supported discovered files can be converted into a processing batch.</CardDescription></CardHeader><CardContent>{validation.discoveredFiles.length ? <DataTable columns={fileColumns} data={validation.discoveredFiles} searchPlaceholder="Search discovered files..." /> : <EmptyState title="No files discovered" description="Revalidate the source. Public direct links and local uploads can be discovered immediately; private cloud sources require connector credentials." action={<Button variant="outline" onClick={() => revalidate.mutate()}><RefreshCcw className="h-4 w-4" />Revalidate source</Button>} />}</CardContent></Card>
    </>
  );
}
