import { ColumnDef } from "@tanstack/react-table";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardCheck, FileText, RefreshCw, Send, ShieldAlert } from "lucide-react";
import type { BatchAuditEvent, BatchEntryPreview, BatchError, FileDiscoveryItem } from "@/types";
import { batchApi } from "@/services/batchApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { LoadingState } from "@/components/common/LoadingState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable } from "@/components/common/DataTable";
import { ProcessingTimeline } from "@/components/common/ProcessingTimeline";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency, formatDateTime, formatNumber, formatPercent } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";
import { ErrorState } from "@/components/common/ErrorState";

const fileColumns: ColumnDef<FileDiscoveryItem>[] = [
  { accessorKey: "fileName", header: "File", cell: ({ row }) => <div><p className="font-semibold">{row.original.fileName}</p><p className="text-xs text-slate-500">{row.original.path}</p></div> },
  { accessorKey: "mimeType", header: "Type" },
  { accessorKey: "sizeBytes", header: "Size", cell: ({ row }) => `${formatNumber(row.original.sizeBytes / 1024)} KB` },
  { accessorKey: "status", header: "Status", cell: ({ row }) => row.original.status === "supported" ? <Badge variant="success">Supported</Badge> : <Badge variant="warning">{row.original.status}</Badge> },
  { accessorKey: "reason", header: "Reason", cell: ({ row }) => row.original.reason ?? "Accepted" },
];

const entryColumns: ColumnDef<BatchEntryPreview>[] = [
  { accessorKey: "id", header: "Entry ID" },
  { accessorKey: "document", header: "Document" },
  { accessorKey: "vendor", header: "Vendor" },
  { accessorKey: "category", header: "Category", cell: ({ row }) => <Badge variant="brand">{row.original.category}</Badge> },
  { accessorKey: "amount", header: "Amount", cell: ({ row }) => formatCurrency(row.original.amount, row.original.currency) },
  { accessorKey: "confidence", header: "Confidence", cell: ({ row }) => formatPercent(row.original.confidence) },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
];

const errorColumns: ColumnDef<BatchError>[] = [
  { accessorKey: "fileName", header: "File" },
  { accessorKey: "stage", header: "Stage" },
  { accessorKey: "message", header: "Message" },
  { accessorKey: "severity", header: "Severity", cell: ({ row }) => <Badge variant={row.original.severity === "critical" ? "danger" : row.original.severity === "error" ? "warning" : "neutral"}>{row.original.severity}</Badge> },
  { accessorKey: "retryable", header: "Retryable", cell: ({ row }) => row.original.retryable ? <Badge variant="info">Yes</Badge> : <Badge variant="neutral">No</Badge> },
  { accessorKey: "createdAt", header: "Created", cell: ({ row }) => formatDateTime(row.original.createdAt) },
];

const auditColumns: ColumnDef<BatchAuditEvent>[] = [
  { accessorKey: "createdAt", header: "Time", cell: ({ row }) => formatDateTime(row.original.createdAt) },
  { accessorKey: "actor", header: "Actor" },
  { accessorKey: "action", header: "Action" },
  { accessorKey: "details", header: "Details" },
];

export function BatchDetailPage() {
  const { batchId = "" } = useParams();
  const toast = useToast();
  const batch = useQuery({ queryKey: ["batch", batchId], queryFn: () => batchApi.getBatch(batchId) });
  const retryMutation = useMutation({
    mutationFn: () => batchApi.retryBatch(batchId),
    onSuccess: async () => {
      toast.success("Batch retry queued");
      await batch.refetch();
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to retry batch"),
  });

  if (batch.isLoading) return <LoadingState />;
  if (batch.isError || !batch.data) return <ErrorState description="Batch detail could not be loaded" onRetry={() => batch.refetch()} />;
  const item = batch.data;

  return (
    <>
      <PageHeader
        eyebrow="Batch detail"
        title={item.id}
        badge={item.status.replaceAll("_", " ")}
        description={`${item.client} · ${item.sourceName} · Created ${formatDateTime(item.createdAt)}`}
        actions={
          <>
            <Button asChild variant="outline"><Link to="/app/ingestion/batches">Back to batches</Link></Button>
            <Button disabled={retryMutation.isPending} onClick={() => retryMutation.mutate()}><RefreshCw className={`h-4 w-4 ${retryMutation.isPending ? "animate-spin" : ""}`} />Retry batch</Button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-5">
        <MetricCard label="Total files" value={String(item.totalFiles)} tone="info" icon={FileText} />
        <MetricCard label="Processed files" value={String(item.processedFiles)} tone="success" icon={CheckCircle2} />
        <MetricCard label="Failed files" value={String(item.failedFiles)} tone={item.failedFiles ? "danger" : "success"} icon={AlertTriangle} />
        <MetricCard label="Pending review" value={String(item.pendingReview)} tone="warning" icon={ClipboardCheck} />
        <MetricCard label="Posted entries" value={String(item.postedEntries)} tone="success" icon={Send} />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Batch overview</CardTitle>
          <CardDescription>Source type, review status, extraction totals, and posting readiness.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 text-sm md:grid-cols-4">
            <div><dt className="text-slate-500">Client</dt><dd className="mt-1 font-semibold">{item.client}</dd></div>
            <div><dt className="text-slate-500">Source type</dt><dd className="mt-1 font-semibold">{item.sourceType}</dd></div>
            <div><dt className="text-slate-500">Extracted entries</dt><dd className="mt-1 font-semibold">{item.extractedEntries}</dd></div>
            <div><dt className="text-slate-500">Status</dt><dd className="mt-1"><StatusBadge status={item.status} /></dd></div>
          </dl>
        </CardContent>
      </Card>

      <Tabs defaultValue="files" className="mt-6">
        <TabsList className="flex h-auto flex-wrap justify-start">
          <TabsTrigger value="files">Files</TabsTrigger>
          <TabsTrigger value="entries">Entries</TabsTrigger>
          <TabsTrigger value="timeline">Processing Timeline</TabsTrigger>
          <TabsTrigger value="errors">Errors</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="files">
          <Card>
            <CardHeader><CardTitle>Files</CardTitle><CardDescription>File discovery table for this batch.</CardDescription></CardHeader>
            <CardContent><DataTable columns={fileColumns} data={item.discoveredFiles} searchPlaceholder="Search files..." /></CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entries">
          <Card>
            <CardHeader><CardTitle>Entries</CardTitle><CardDescription>Extracted accounting entries generated from the batch files.</CardDescription></CardHeader>
            <CardContent><DataTable columns={entryColumns} data={item.entryPreviews} searchPlaceholder="Search entries..." /></CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>Processing Timeline</CardTitle>
              <CardDescription>Link validated → Files discovered → Files downloaded → Virus scan → OCR/extraction → Classification → SAP/accounting mapping → Validation → Review → Posting.</CardDescription>
            </CardHeader>
            <CardContent><ProcessingTimeline steps={item.timeline} /></CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="errors">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><ShieldAlert className="h-5 w-5 text-danger" />Errors</CardTitle>
              <CardDescription>Retryable and non-retryable issues found during ingestion, extraction, validation, or posting.</CardDescription>
            </CardHeader>
            <CardContent>
              {item.errors.length ? <DataTable columns={errorColumns} data={item.errors} searchPlaceholder="Search errors..." /> : <div className="rounded-2xl border border-success/30 bg-success/10 p-6 text-sm text-success">No errors found for this batch.</div>}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader><CardTitle>Audit</CardTitle><CardDescription>Immutable activity history for enterprise traceability.</CardDescription></CardHeader>
            <CardContent><DataTable columns={auditColumns} data={item.audit} searchPlaceholder="Search audit events..." /></CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
