import { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ClipboardList, Layers3, RotateCw } from "lucide-react";
import type { IngestionBatch } from "@/types";
import { batchApi } from "@/services/batchApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";

const columns: ColumnDef<IngestionBatch>[] = [
  { accessorKey: "id", header: "Batch ID", cell: ({ row }) => <Link className="font-semibold text-primary hover:underline" to={`/app/ingestion/batches/${row.original.id}`}>{row.original.id}</Link> },
  { accessorKey: "client", header: "Client" },
  { accessorKey: "sourceType", header: "Source type" },
  { accessorKey: "totalFiles", header: "Total files", cell: ({ row }) => <span className="font-semibold tabular">{row.original.totalFiles}</span> },
  { accessorKey: "processedFiles", header: "Processed files", cell: ({ row }) => <span className="font-semibold tabular">{row.original.processedFiles}</span> },
  { accessorKey: "failedFiles", header: "Failed files", cell: ({ row }) => <span className="font-semibold tabular text-danger">{row.original.failedFiles}</span> },
  { accessorKey: "extractedEntries", header: "Extracted entries", cell: ({ row }) => <span className="font-semibold tabular">{row.original.extractedEntries}</span> },
  { accessorKey: "pendingReview", header: "Pending review", cell: ({ row }) => <span className="font-semibold tabular">{row.original.pendingReview}</span> },
  { accessorKey: "postedEntries", header: "Posted entries", cell: ({ row }) => <span className="font-semibold tabular text-success">{row.original.postedEntries}</span> },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
  { accessorKey: "createdAt", header: "Created date", cell: ({ row }) => formatDateTime(row.original.createdAt) },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => (
      <Button asChild size="sm" variant="outline">
        <Link to={`/app/ingestion/batches/${row.original.id}`}>Open</Link>
      </Button>
    ),
  },
];

export function BatchesPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["batches"], queryFn: batchApi.getBatches });
  const retryMutation = useMutation({ mutationFn: batchApi.retryFailedBatches, onSuccess: (result) => toast.success("Failed batches queued", `${result.retried} batch(es) moved to processing.`), onError: (error) => toast.error("Retry failed", error instanceof Error ? error.message : "Unknown error") });
  const batches = query.data ?? [];
  const totalFiles = batches.reduce((sum, batch) => sum + batch.totalFiles, 0);
  const pendingReview = batches.reduce((sum, batch) => sum + batch.pendingReview, 0);
  const failedFiles = batches.reduce((sum, batch) => sum + batch.failedFiles, 0);

  return (
    <>
      <PageHeader
        eyebrow="Ingestion"
        title="Processing batches"
        description="Track discovered files, batch processing status, extraction progress, review workload, posting status, and retry operations."
        actions={<Button variant="outline" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate()}><RotateCw className={`h-4 w-4 ${retryMutation.isPending ? "animate-spin" : ""}`} />Retry failed</Button>}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Batches" value={String(batches.length)} tone="neutral" icon={Layers3} />
        <MetricCard label="Total files" value={String(totalFiles)} tone="info" icon={ClipboardList} />
        <MetricCard label="Pending review" value={String(pendingReview)} tone="warning" icon={CheckCircle2} />
        <MetricCard label="Failed files" value={String(failedFiles)} tone={failedFiles ? "danger" : "success"} icon={AlertTriangle} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Layers3 className="h-5 w-5 text-primary" />Batch runs</CardTitle>
          <CardDescription>One processable batch is created from each shared-link sync, manual URL list, or local upload run.</CardDescription>
        </CardHeader>
        <CardContent>{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState description="Batches could not be loaded" onRetry={() => query.refetch()} /> : batches.length === 0 ? <EmptyState title="No processing batches yet" description="Validate a shared link and use Create Batch to discover, import, and process its files." action={<Button asChild><Link to="/app/ingestion/shared-links">Open shared links</Link></Button>} /> : <DataTable columns={columns} data={batches} searchPlaceholder="Search batches..." />}</CardContent>
      </Card>
    </>
  );
}
