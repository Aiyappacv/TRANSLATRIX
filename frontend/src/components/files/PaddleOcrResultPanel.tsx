import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Cloud, PlayCircle, RefreshCw, ScanLine } from "lucide-react";
import type { IngestedFile } from "@/types";
import { fileApi } from "@/services/fileApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { formatDateTime } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";
import { usePermissions } from "@/hooks/usePermissions";
import { permissions } from "@/utils/permissions";

export function PaddleOcrResultPanel({ file }: { file: IngestedFile }) {
  const ocr = file.ocr;
  const toast = useToast();
  const { hasPermission } = usePermissions();
  const canProcess = hasPermission(permissions.filesProcess);
  const queryClient = useQueryClient();
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["file", file.id] }),
      queryClient.invalidateQueries({ queryKey: ["files"] }),
      queryClient.invalidateQueries({ queryKey: ["entries"] }),
      queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
    ]);
  };
  const process = useMutation({ mutationFn: () => fileApi.processFile(file.id), onSuccess: async () => { await refresh(); toast.success("Processing completed", "OCR, extraction, validation, and review routing were refreshed."); }, onError: (error) => toast.error("Processing failed", error instanceof Error ? error.message : "Unknown error") });
  const retry = useMutation({ mutationFn: () => fileApi.retryOcr(file.id), onSuccess: async () => { await refresh(); toast.success("OCR completed", "The document was processed again."); }, onError: (error) => toast.error("OCR retry failed", error instanceof Error ? error.message : "Unknown error") });
  const fallback = useMutation({ mutationFn: () => fileApi.runCloudOcrFallback(file.id), onSuccess: async () => { await refresh(); toast.success("Cloud OCR completed"); }, onError: (error) => toast.error("Cloud OCR unavailable", error instanceof Error ? error.message : "Configure a cloud OCR provider first") });

  if (!ocr) {
    return (
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><ScanLine className="h-5 w-5 text-primary" />OCR has not started</CardTitle><CardDescription>Start document processing to run OCR, extraction, validation, and review-task generation.</CardDescription></CardHeader>
        <CardContent>{canProcess ? <Button onClick={() => process.mutate()} disabled={process.isPending}><PlayCircle className="h-4 w-4" />{process.isPending ? "Processing..." : "Start processing"}</Button> : <p className="text-sm text-slate-500">You have read-only access to this document.</p>}</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><CardTitle className="flex items-center gap-2"><ScanLine className="h-5 w-5 text-primary" />OCR result</CardTitle><CardDescription>{ocr.engine} {ocr.engineVersion} · {ocr.pageCount} page{ocr.pageCount === 1 ? "" : "s"} · {ocr.languageDetected}</CardDescription></div>
          {canProcess ? <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => retry.mutate()} disabled={retry.isPending}><RefreshCw className={`h-4 w-4 ${retry.isPending ? "animate-spin" : ""}`} />Retry OCR</Button>
            <Button variant="outline" onClick={() => fallback.mutate()} disabled={fallback.isPending}><Cloud className="h-4 w-4" />Cloud fallback</Button>
          </div> : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-center gap-2"><Badge variant={ocr.status === "completed" ? "success" : ocr.status === "failed" ? "danger" : "warning"}>{ocr.status}</Badge><span className="text-xs text-slate-500">Started {formatDateTime(ocr.startedAt)}{ocr.completedAt ? ` · Completed ${formatDateTime(ocr.completedAt)}` : ""}</span></div>
        <ConfidenceBar label="OCR confidence" value={ocr.overallConfidence} />
        <div className="space-y-4">
          {ocr.pages.map((page) => (
            <div key={page.pageNumber} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
              <div className="mb-3 flex items-center justify-between"><p className="font-semibold">Page {page.pageNumber}</p><Badge variant={page.confidence >= 0.85 ? "success" : "warning"}>{Math.round(page.confidence * 100)}%</Badge></div>
              <div className="space-y-2">
                {page.blocks.length ? page.blocks.map((block) => <div key={block.id} className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-900"><div className="mb-1 flex items-center justify-between"><span className="text-xs font-semibold uppercase text-slate-500">{block.type}</span><span className="text-xs text-slate-500">{Math.round(block.confidence * 100)}%</span></div><p className="whitespace-pre-wrap">{block.text}</p><p className="mt-1 text-[11px] text-slate-400">bbox: {block.bbox.join(", ")}</p></div>) : <p className="text-sm text-slate-500">No OCR blocks were returned for this page.</p>}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
