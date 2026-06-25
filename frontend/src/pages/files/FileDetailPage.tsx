import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BookOpenText, Code2, Download, FileText, ListTree, PlayCircle, ScanLine, Table2, Trash2, Workflow } from "lucide-react";
import { fileApi } from "@/services/fileApi";
import { entryApi } from "@/services/entryApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { MetricCard } from "@/components/common/MetricCard";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { OriginalFilePreview } from "@/components/files/OriginalFilePreview";
import { PaddleOcrResultPanel } from "@/components/files/PaddleOcrResultPanel";
import { ExtractedTablesGrid } from "@/components/files/ExtractedTablesGrid";
import { ProcessingLogsPanel } from "@/components/files/ProcessingLogsPanel";
import { ProcessingStatusTimeline } from "@/components/files/ProcessingStatusTimeline";
import { ExtractionJsonViewer } from "@/components/files/ExtractionJsonViewer";
import { FinancialEntryTable } from "@/components/entries/FinancialEntryTable";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/utils/formatters";
import { usePermissions } from "@/hooks/usePermissions";
import { permissions } from "@/utils/permissions";

export function FileDetailPage() {
  const { fileId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const canProcess = hasPermission(permissions.filesProcess);
  const canManage = hasPermission(permissions.filesManage);
  const [tab, setTab] = useState("original");
  const file = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => fileApi.getFile(fileId),
    enabled: Boolean(fileId),
    refetchInterval: (query) => {
      if (query.state.status === "error") return false;
      const data = query.state.data;
      if (!data) return 2000;
      if (data.status === "uploaded" || data.status === "processing") return 2000;
      return false;
    },
  });
  const entries = useQuery({ queryKey: ["entries"], queryFn: entryApi.getEntries });
  const refresh = async () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["file", fileId] }),
    queryClient.invalidateQueries({ queryKey: ["files"] }),
    queryClient.invalidateQueries({ queryKey: ["entries"] }),
    queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
    queryClient.invalidateQueries({ queryKey: ["analytics"] }),
  ]);
  const process = useMutation({ mutationFn: () => fileApi.processFile(fileId), onSuccess: async () => { await refresh(); setTab("ocr"); toast.success("Document processing completed"); }, onError: (error) => toast.error(error instanceof Error ? error.message : "Processing failed") });
  const download = useMutation({ mutationFn: () => fileApi.downloadFile(fileId, file.data?.fileName ?? "file"), onSuccess: () => toast.success("File download started"), onError: (error) => toast.error(error instanceof Error ? error.message : "Download failed") });
  const downloadJson = useMutation({ mutationFn: () => fileApi.downloadExtractionJson(fileId, `extraction_${fileId.slice(0, 8)}.json`), onSuccess: () => toast.success("JSON download started"), onError: (error) => toast.error(error instanceof Error ? error.message : "JSON download failed") });
  const remove = useMutation({ mutationFn: () => fileApi.deleteFile(fileId), onSuccess: async () => { await refresh(); toast.success("File deleted"); navigate("/app/files"); }, onError: (error) => toast.error(error instanceof Error ? error.message : "Delete failed") });

  if (file.isLoading) return <LoadingState />;
  if (file.isError || !file.data) return <ErrorState description="File detail could not be loaded" onRetry={() => file.refetch()} />;
  const isProcessing = file.data.status === "uploaded" || file.data.status === "processing";

  const doc = file.data;
  const fileEntries = (entries.data ?? []).filter((entry) => entry.fileId === fileId);
  const uploader = doc.uploadedBy;

  return (
    <>
      <PageHeader
        eyebrow="File detail"
        title={doc.fileName}
        badge={doc.extractionMethod || "Pending processing"}
        description={`${doc.source} · ${doc.batchId || "No batch"} · Created ${formatDateTime(doc.createdAt)} · Checksum ${doc.checksum}`}
        actions={<>
          <Button asChild variant="outline"><Link to="/app/files">Back</Link></Button>
          <Button variant="outline" onClick={() => download.mutate()} disabled={download.isPending}><Download className="h-4 w-4" />Download</Button>
          {doc.extractionJson ? <Button variant="outline" onClick={() => downloadJson.mutate()} disabled={downloadJson.isPending}><Code2 className="h-4 w-4" />{downloadJson.isPending ? "Downloading..." : "Download JSON"}</Button> : null}
          {canProcess ? <Button onClick={() => process.mutate()} disabled={process.isPending}><PlayCircle className="h-4 w-4" />{process.isPending ? "Processing..." : doc.ocr ? "Reprocess file" : "Start processing"}</Button> : null}
          {canManage ? <ConfirmDialog trigger={<Button variant="destructive"><Trash2 className="h-4 w-4" />Delete</Button>} title="Delete file?" description="This also removes generated entries, review tasks, and posting records." confirmLabel="Delete file" onConfirm={() => remove.mutateAsync()} /> : null}
        </>}
      />

      <div className="grid gap-4 md:grid-cols-5">
        <MetricCard label="OCR status" value={doc.ocrStatus} tone={doc.ocrStatus === "completed" ? "success" : doc.ocrStatus === "failed" ? "danger" : "warning"} icon={ScanLine} />
        <MetricCard label="Extraction status" value={doc.extractionStatus} tone={doc.extractionStatus === "completed" ? "success" : doc.extractionStatus === "failed" ? "danger" : "warning"} icon={BookOpenText} />
        <MetricCard label="Entries extracted" value={String(doc.entriesExtracted)} tone="info" icon={FileText} />
        <MetricCard label="Confidence" value={`${Math.round(doc.confidence * 100)}%`} tone={doc.confidence >= 0.9 ? "success" : doc.confidence >= 0.8 ? "warning" : "danger"} icon={Workflow} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_380px]">
        <OriginalFilePreview file={doc} />
        <Card><CardHeader><CardTitle>Document intelligence summary</CardTitle><CardDescription>Processing context, uploader identity, and review readiness.</CardDescription></CardHeader><CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2"><StatusBadge status={doc.status} /><Badge variant="brand">{doc.type}</Badge><Badge variant="neutral">{doc.sourceLanguage}</Badge></div>
          <ConfidenceBar label="Overall confidence" value={doc.confidence} />
          <dl className="grid gap-3 text-sm">
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><dt className="text-xs text-slate-500">Uploaded by</dt><dd className="font-semibold">{uploader?.name ?? "System/import"}</dd>{uploader ? <dd className="text-xs text-slate-500">{uploader.email} · {uploader.role}</dd> : null}</div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><dt className="text-xs text-slate-500">Uploaded at</dt><dd className="font-semibold">{formatDateTime(doc.uploadedAt)}</dd></div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><dt className="text-xs text-slate-500">Source / batch</dt><dd className="font-semibold">{doc.source} · {doc.batchName || "No batch"}</dd></div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><dt className="text-xs text-slate-500">MIME / size</dt><dd className="font-semibold">{doc.mimeType} · {Math.round(doc.sizeBytes / 1024)} KB</dd></div>
          </dl>
        </CardContent></Card>
      </div>

      {isProcessing ? (
        <div className="mt-6">
          <ProcessingStatusTimeline file={doc} onRefresh={refresh} />
        </div>
      ) : (
      <Tabs value={tab} onValueChange={setTab} className="mt-6">
        <TabsList className="flex h-auto flex-wrap justify-start">
          <TabsTrigger value="original"><FileText className="mr-2 h-4 w-4" />Original Preview</TabsTrigger>
          <TabsTrigger value="ocr"><ScanLine className="mr-2 h-4 w-4" />OCR Result</TabsTrigger>
          <TabsTrigger value="text"><BookOpenText className="mr-2 h-4 w-4" />Extracted Text</TabsTrigger>
          <TabsTrigger value="json"><Code2 className="mr-2 h-4 w-4" />JSON View</TabsTrigger>
          <TabsTrigger value="tables"><Table2 className="mr-2 h-4 w-4" />Extracted Tables</TabsTrigger>
          <TabsTrigger value="entries"><ListTree className="mr-2 h-4 w-4" />Entries</TabsTrigger>
          <TabsTrigger value="logs"><Workflow className="mr-2 h-4 w-4" />Processing Logs</TabsTrigger>
        </TabsList>
        <TabsContent value="original"><OriginalFilePreview file={doc} /></TabsContent>
        <TabsContent value="ocr"><PaddleOcrResultPanel file={doc} /></TabsContent>
        <TabsContent value="text"><Card><CardHeader><CardTitle>Extracted Text</CardTitle><CardDescription>Raw text produced before classification.</CardDescription></CardHeader><CardContent><pre className="max-h-[560px] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">{doc.extractedText || "No extracted text available. Run processing to generate it."}</pre></CardContent></Card></TabsContent>
        <TabsContent value="json"><ExtractionJsonViewer json={doc.extractionJson ?? null} loading={file.isLoading} fileId={fileId} /></TabsContent>
        <TabsContent value="tables"><Card><CardHeader><CardTitle>Extracted Tables</CardTitle><CardDescription>Review and correct detected table rows.</CardDescription></CardHeader><CardContent><ExtractedTablesGrid fileId={doc.id} tables={doc.extractedTables} /></CardContent></Card></TabsContent>
        <TabsContent value="entries"><Card><CardHeader><CardTitle>Entries</CardTitle><CardDescription>Accounting entries generated from this file.</CardDescription></CardHeader><CardContent>{entries.isLoading ? <LoadingState /> : <FinancialEntryTable entries={fileEntries} />}</CardContent></Card></TabsContent>
        <TabsContent value="logs"><Card><CardHeader><CardTitle>Processing Logs</CardTitle><CardDescription>Timeline of jobs, statuses, errors, and retry controls.</CardDescription></CardHeader><CardContent><ProcessingLogsPanel fileId={doc.id} logs={doc.processingLogs} /></CardContent></Card></TabsContent>
      </Tabs>
      )}
    </>
  );
}
