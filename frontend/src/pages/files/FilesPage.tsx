import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Download, Files, ScanLine, Trash2, UploadCloud } from "lucide-react";
import type { IngestedFile } from "@/types";
import { fileApi } from "@/services/fileApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FileDropzone } from "@/components/common/FileDropzone";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { formatDateTime } from "@/utils/formatters";
import { usePermissions } from "@/hooks/usePermissions";
import { permissions } from "@/utils/permissions";

const workerBadge = (status: IngestedFile["ocrStatus"]) => {
  const variant = status === "completed" ? "success" : status === "failed" ? "danger" : status === "processing" ? "info" : "warning";
  return <Badge variant={variant}>{status}</Badge>;
};

export function FilesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const canUpload = hasPermission(permissions.filesUpload);
  const canManage = hasPermission(permissions.filesManage);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const query = useQuery({ queryKey: ["files"], queryFn: fileApi.getFiles });
  const upload = useMutation({
    mutationFn: async () => Promise.all(selectedFiles.map((file) => fileApi.uploadLocalFile(file))),
    onSuccess: async (created) => {
      setSelectedFiles([]);
      setUploadOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["files"] }),
        queryClient.invalidateQueries({ queryKey: ["document-registry"] }),
      ]);
      if (created.length === 1) {
        navigate(`/app/files/${created[0].id}`);
      } else {
        toast.success(`${created.length} files uploaded`);
      }
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Local upload failed"),
  });
  const download = useMutation({
    mutationFn: (file: IngestedFile) => fileApi.downloadFile(file.id, file.fileName),
    onSuccess: () => toast.success("File download started"),
    onError: (error) => toast.error(error instanceof Error ? error.message : "File download failed"),
  });
  const remove = useMutation({
    mutationFn: (file: IngestedFile) => fileApi.deleteFile(file.id),
    onSuccess: async () => {
      toast.success("File deleted");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["files"] }),
        queryClient.invalidateQueries({ queryKey: ["entries"] }),
        queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "File deletion failed"),
  });

  const columns = useMemo<ColumnDef<IngestedFile>[]>(() => [
    {
      accessorKey: "fileName",
      header: "File name",
      cell: ({ row }) => (
        <div>
          <Link className="font-semibold text-primary hover:underline" to={`/app/files/${row.original.id}`}>{row.original.fileName}</Link>
          <p className="text-xs text-slate-500">{row.original.mimeType}</p>
        </div>
      ),
    },
    { accessorKey: "type", header: "Type", cell: ({ row }) => <Badge variant="brand">{row.original.type}</Badge> },
    { accessorKey: "source", header: "Source" },
    { accessorKey: "batchId", header: "Batch", cell: ({ row }) => row.original.batchId ? <Link className="text-primary hover:underline" to={`/app/ingestion/batches/${row.original.batchId}`}>{row.original.batchId}</Link> : "—" },
    {
      id: "uploadedBy",
      header: "Uploaded by",
      cell: ({ row }) => row.original.uploadedBy ? (
        <div><p className="font-medium">{row.original.uploadedBy.name}</p><p className="text-xs text-slate-500">{row.original.uploadedBy.role} · {row.original.uploadedBy.email}</p></div>
      ) : <span className="text-slate-500">System/import</span>,
    },
    { accessorKey: "ocrStatus", header: "OCR status", cell: ({ row }) => workerBadge(row.original.ocrStatus) },
    { accessorKey: "extractionStatus", header: "Extraction status", cell: ({ row }) => workerBadge(row.original.extractionStatus) },
    { accessorKey: "entriesExtracted", header: "Entries", cell: ({ row }) => <span className="font-semibold tabular">{row.original.entriesExtracted}</span> },
    { accessorKey: "confidence", header: "Confidence", cell: ({ row }) => <div className="w-32"><ConfidenceBar label="" value={row.original.confidence} compact /></div> },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
    { accessorKey: "createdAt", header: "Created", cell: ({ row }) => formatDateTime(row.original.createdAt) },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm" variant="outline"><Link to={`/app/files/${row.original.id}`}>Open</Link></Button>
          <Button size="sm" variant="outline" disabled={download.isPending} onClick={() => download.mutate(row.original)}><Download className="h-4 w-4" />Download</Button>
          {canManage ? (
            <ConfirmDialog
              title="Delete file?"
              description={`Delete ${row.original.fileName} and its generated entries, review tasks, and posting records? This cannot be undone.`}
              confirmLabel="Delete file"
              trigger={<Button size="sm" variant="destructive"><Trash2 className="h-4 w-4" />Delete</Button>}
              onConfirm={() => remove.mutateAsync(row.original)}
            />
          ) : null}
        </div>
      ),
    },
  ], [canManage, download, remove]);

  const files = query.data ?? [];
  const failed = files.filter((file) => file.status === "validation_failed" || file.ocrStatus === "failed" || file.extractionStatus === "failed").length;
  const entries = files.reduce((sum, file) => sum + file.entriesExtracted, 0);

  return (
    <>
      <PageHeader
        eyebrow="Document intelligence"
        title="Files"
        description="Track original files, OCR, extraction, entries, uploader audit data, confidence, and processing status."
        actions={canUpload ? <Button onClick={() => setUploadOpen(true)}><UploadCloud className="h-4 w-4" />Upload local file</Button> : undefined}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Files" value={String(files.length)} tone="info" icon={Files} />
        <MetricCard label="OCR completed" value={String(files.filter((file) => file.ocrStatus === "completed").length)} tone="success" icon={ScanLine} />
        <MetricCard label="Extracted" value={String(files.filter((file) => file.extractionStatus === "completed").length)} tone="success" icon={CheckCircle2} />
        <MetricCard label="Issues" value={String(failed)} tone={failed ? "danger" : "success"} icon={failed ? AlertTriangle : CheckCircle2} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>File processing queue</CardTitle>
          <CardDescription>{entries} entries extracted. Upload starts the local processing pipeline automatically; failed steps can be retried from file details.</CardDescription>
        </CardHeader>
        <CardContent>
          {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState description="Files could not be loaded" onRetry={() => query.refetch()} /> : files.length ? <DataTable columns={columns} data={files} searchPlaceholder="Search files, batches, sources, uploaders..." exportFileName="translatrix-files" /> : <EmptyState title="No files yet" description="Upload a PDF, image, spreadsheet, CSV, or DOCX file to start OCR, extraction, validation, and review routing." action={canUpload ? <Button onClick={() => setUploadOpen(true)}><UploadCloud className="h-4 w-4" />Upload first file</Button> : undefined} />}
        </CardContent>
      </Card>
      {canUpload ? <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Upload local financial files</DialogTitle><DialogDescription>Files are stored securely and processed immediately using the enabled document-processing settings.</DialogDescription></DialogHeader>
          <FileDropzone accept=".pdf,.png,.jpg,.jpeg,.webp,.csv,.xlsx,.docx,.txt" onFiles={setSelectedFiles} />
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button><Button onClick={() => upload.mutate()} disabled={!selectedFiles.length || upload.isPending}>{upload.isPending ? "Uploading and processing..." : `Upload ${selectedFiles.length || ""} file${selectedFiles.length === 1 ? "" : "s"}`}</Button></div>
        </DialogContent>
      </Dialog> : null}
    </>
  );
}
