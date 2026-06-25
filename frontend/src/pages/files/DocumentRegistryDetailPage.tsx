import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpenText,
  Clock,
  Code2,
  Download,
  FileText,
  History,
  ListChecks,
  ScanLine,
  Sparkles,
  Trash2,
  Workflow,
} from "lucide-react";
import { toast } from "sonner";
import { documentRegistryApi } from "@/services/documentRegistryApi";
import { fileApi } from "@/services/fileApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PaddleOcrResultPanel } from "@/components/files/PaddleOcrResultPanel";
import { ProcessingLogsPanel } from "@/components/files/ProcessingLogsPanel";
import { ExtractionJsonViewer } from "@/components/files/ExtractionJsonViewer";
import { formatDateTime } from "@/utils/formatters";

function FieldRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900">
      <span className="font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-slate-800 dark:text-slate-200">{value === null || value === undefined || value === "" ? <span className="text-slate-400">—</span> : value}</span>
    </div>
  );
}

export function DocumentRegistryDetailPage() {
  const { fileId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "summary";

  const registry = useQuery({
    queryKey: ["document-registry-entry", fileId],
    queryFn: () => documentRegistryApi.get(fileId),
    enabled: Boolean(fileId),
  });
  const file = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => fileApi.getFile(fileId),
    enabled: Boolean(fileId),
    refetchInterval: (query) => {
      if (query.state.status === "error") return false;
      const data = query.state.data;
      if (!data) return 2000;
      return data.status === "uploaded" || data.status === "processing" ? 2000 : false;
    },
  });

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["document-registry-entry", fileId] }),
      queryClient.invalidateQueries({ queryKey: ["file", fileId] }),
      queryClient.invalidateQueries({ queryKey: ["document-registry"] }),
    ]);

  const reprocess = useMutation({
    mutationFn: () => documentRegistryApi.reprocess(fileId),
    onSuccess: async () => { await refresh(); toast.success("Document reprocessed"); },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Reprocess failed"),
  });
  const remove = useMutation({
    mutationFn: () => documentRegistryApi.delete(fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-registry"] });
      toast.success("Registry entry deleted");
      navigate("/app/files/registry");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Delete failed"),
  });

  if (registry.isLoading || file.isLoading) return <LoadingState label="Loading registry entry..." />;
  if (registry.isError || !registry.data) return <ErrorState description="Registry entry could not be loaded" onRetry={() => registry.refetch()} />;

  const entry = registry.data;
  const doc = file.data;

  return (
    <>
      <PageHeader
        eyebrow="Document Registry"
        title={entry.originalFileName}
        badge={entry.status.replace(/_/g, " ")}
        description={`Document ID ${entry.id} · Uploaded ${entry.uploadedAt ? formatDateTime(entry.uploadedAt) : "—"} by ${entry.uploadedBy || "Unknown"}`}
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/app/files/registry"><ArrowLeft className="h-4 w-4" />Back to Registry</Link>
            </Button>
            <Button variant="outline" onClick={() => fileApi.downloadFile(entry.id, entry.originalFileName)}>
              <Download className="h-4 w-4" />Download Original
            </Button>
            <Button variant="outline" onClick={() => {
              fileApi.downloadExtractionJson(entry.id, `${entry.originalFileName}.json`)
                .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
            }}>
              <Code2 className="h-4 w-4" />Download JSON
            </Button>
            <Button onClick={() => reprocess.mutate()} disabled={reprocess.isPending}>
              <Sparkles className="h-4 w-4" />{reprocess.isPending ? "Reprocessing..." : "Reprocess"}
            </Button>
            <ConfirmDialog
              trigger={<Button variant="destructive"><Trash2 className="h-4 w-4" />Delete</Button>}
              title="Delete registry entry?"
              description="This permanently removes the document and all associated extraction results, entries, and review tasks."
              confirmLabel="Delete permanently"
              onConfirm={() => remove.mutateAsync()}
            />
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <Card>
          <CardContent className="pt-6">
            <ConfidenceBar label="Overall extraction confidence" value={entry.overallConfidence ?? 0} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <ConfidenceBar label="OCR confidence" value={entry.ocrConfidence ?? 0} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <ConfidenceBar label="Field extraction confidence" value={entry.fieldExtractionConfidence ?? 0} />
          </CardContent>
        </Card>
      </div>

      <Tabs value={tab} onValueChange={(value) => setSearchParams(value === "summary" ? {} : { tab: value })}>
        <TabsList className="flex h-auto flex-wrap justify-start">
          <TabsTrigger value="summary"><FileText className="mr-2 h-4 w-4" />Summary</TabsTrigger>
          <TabsTrigger value="fields"><ListChecks className="mr-2 h-4 w-4" />Extracted Fields</TabsTrigger>
          <TabsTrigger value="ocr"><ScanLine className="mr-2 h-4 w-4" />OCR Results</TabsTrigger>
          <TabsTrigger value="logs"><Workflow className="mr-2 h-4 w-4" />Processing Logs</TabsTrigger>
          <TabsTrigger value="audit"><History className="mr-2 h-4 w-4" />Audit Trail</TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Document Information</CardTitle><CardDescription>Core metadata for this registry entry.</CardDescription></CardHeader>
              <CardContent className="space-y-2">
                <FieldRow label="Document ID" value={entry.id} />
                <FieldRow label="Original File Name" value={entry.originalFileName} />
                <FieldRow label="Document Type" value={entry.documentType} />
                <FieldRow label="Source Channel" value={entry.sourceChannel} />
                <FieldRow label="Upload Date & Time" value={entry.uploadedAt ? formatDateTime(entry.uploadedAt) : null} />
                <FieldRow label="Processing Date & Time" value={entry.processedAt ? formatDateTime(entry.processedAt) : null} />
                <FieldRow label="Uploaded By" value={entry.uploadedBy} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Extraction Information</CardTitle><CardDescription>Pipeline status and engine details.</CardDescription></CardHeader>
              <CardContent className="space-y-2">
                <FieldRow label="Extraction Status" value={entry.status.replace(/_/g, " ")} />
                <FieldRow label="OCR Engine Used" value={entry.ocrEngine} />
                <FieldRow label="Processing Time" value={entry.processingTimeSeconds != null ? `${entry.processingTimeSeconds.toFixed(2)}s` : null} />
                <FieldRow label="Total Pages" value={entry.totalPages} />
                <FieldRow label="Language Detected" value={entry.languageDetected} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Quality Metrics</CardTitle><CardDescription>Confidence and validation scores.</CardDescription></CardHeader>
              <CardContent className="space-y-2">
                <FieldRow label="Overall Extraction Confidence" value={entry.overallConfidence != null ? `${Math.round(entry.overallConfidence * 100)}%` : null} />
                <FieldRow label="OCR Confidence" value={entry.ocrConfidence != null ? `${Math.round(entry.ocrConfidence * 100)}%` : null} />
                <FieldRow label="Field Extraction Confidence" value={entry.fieldExtractionConfidence != null ? `${Math.round(entry.fieldExtractionConfidence * 100)}%` : null} />
                <FieldRow label="Validation Score" value={entry.validationScore != null ? `${Math.round(entry.validationScore * 100)}%` : null} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Business Metadata</CardTitle><CardDescription>Extracted document identifiers.</CardDescription></CardHeader>
              <CardContent className="space-y-2">
                <FieldRow label="Invoice Number" value={entry.invoiceNumber} />
                <FieldRow label="Vendor / Supplier" value={entry.vendorName} />
                <FieldRow label="Customer" value={entry.customerName} />
                <FieldRow label="Filing Number" value={entry.filingNumber} />
                <FieldRow label="Shipment Reference" value={entry.shipmentReference} />
                <FieldRow label="Country" value={entry.country} />
                <FieldRow label="Trade Lane" value={entry.tradeLane} />
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>System Metadata</CardTitle><CardDescription>Registry bookkeeping for compliance and traceability.</CardDescription></CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2">
                <FieldRow label="Registry Created" value={entry.registryCreatedAt ? formatDateTime(entry.registryCreatedAt) : null} />
                <FieldRow label="Last Updated" value={entry.lastUpdatedAt ? formatDateTime(entry.lastUpdatedAt) : null} />
                <FieldRow label="Processing Job ID" value={entry.processingJobId} />
                <FieldRow label="Version Number" value={entry.versionNumber} />
                <FieldRow label="Checksum" value={entry.checksum} />
                <FieldRow label="File Size" value={entry.sizeBytes != null ? `${Math.round(entry.sizeBytes / 1024)} KB` : null} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="fields">
          <ExtractionJsonViewer json={entry.extractionJson} loading={registry.isLoading} fileId={entry.id} />
        </TabsContent>

        <TabsContent value="ocr">
          {doc ? <PaddleOcrResultPanel file={doc} /> : <LoadingState />}
          {entry.extractedText ? (
            <Card className="mt-4">
              <CardHeader><CardTitle className="flex items-center gap-2"><BookOpenText className="h-4 w-4" />Raw Extracted Text</CardTitle></CardHeader>
              <CardContent>
                <pre className="max-h-[400px] overflow-auto whitespace-pre-wrap rounded-2xl bg-slate-950 p-4 text-sm leading-6 text-slate-100">{entry.extractedText}</pre>
              </CardContent>
            </Card>
          ) : null}
        </TabsContent>

        <TabsContent value="logs">
          <ProcessingLogsPanel fileId={entry.id} logs={entry.processingLogs} />
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><History className="h-4 w-4" />Audit Trail</CardTitle><CardDescription>Immutable history derived from processing logs and registry metadata.</CardDescription></CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-3">
                <FieldRow label="Created" value={entry.registryCreatedAt ? formatDateTime(entry.registryCreatedAt) : null} />
                <FieldRow label="Last Modified" value={entry.lastUpdatedAt ? formatDateTime(entry.lastUpdatedAt) : null} />
                <FieldRow label="Times Reprocessed" value={entry.versionNumber} />
              </div>
              <div className="space-y-2">
                {entry.processingLogs.length === 0 ? (
                  <p className="text-sm text-slate-400">No processing history recorded yet.</p>
                ) : (
                  entry.processingLogs.map((log) => (
                    <div key={log.id} className="flex items-start gap-3 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-900">
                      <Clock className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-700 dark:text-slate-300">{log.step}</span>
                          <Badge variant={log.status === "completed" ? "success" : log.status === "failed" ? "danger" : "warning"} className="text-xs">{log.status}</Badge>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">{log.message}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{log.worker} · {formatDateTime(log.startedAt)}{log.completedAt ? ` → ${formatDateTime(log.completedAt)}` : ""}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
