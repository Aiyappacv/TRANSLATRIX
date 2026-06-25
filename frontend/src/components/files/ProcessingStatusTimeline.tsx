import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Clock, Code2, Download, Eye, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { IngestedFile, FileProcessingLog } from "@/types";
import { fileApi } from "@/services/fileApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { formatDateTime, formatDuration } from "@/utils/formatters";
import { cn } from "@/utils/cn";

const KNOWN_STAGES = [
  "Initializing",
  "Preprocessing",
  "Document Analysis",
  "Mistral OCR Processing",
  "Field Extraction",
  "Validation",
  "Generating JSON",
  "Extraction Complete",
] as const;

type StageStatus = "pending" | "active" | "completed" | "failed";

function getStageStatus(stage: string, currentStage: string, fileStatus: string): StageStatus {
  const stageIndex = KNOWN_STAGES.indexOf(stage as typeof KNOWN_STAGES[number]);
  const currentIndex = KNOWN_STAGES.indexOf(currentStage as typeof KNOWN_STAGES[number]);
  if (fileStatus === "validation_failed" || fileStatus === "failed") {
    if (stage === currentStage || (currentIndex >= 0 && stageIndex === currentIndex)) return "failed";
    if (currentIndex >= 0 && stageIndex < currentIndex) return "completed";
    return "pending";
  }
  if (currentIndex < 0) {
    const isLogStage = currentStage && stage !== "Extraction Complete";
    if (isLogStage) return stageIndex <= 1 ? "completed" : "pending";
    return "pending";
  }
  if (stageIndex < currentIndex) return "completed";
  if (stageIndex === currentIndex) return "active";
  return "pending";
}

function StageIcon({ status }: { status: StageStatus }) {
  if (status === "completed") return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
  if (status === "active") return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  if (status === "failed") return <AlertTriangle className="h-5 w-5 text-red-500" />;
  return <Clock className="h-5 w-5 text-slate-300 dark:text-slate-600" />;
}

interface ProcessingStatusTimelineProps {
  file: IngestedFile;
  onRefresh?: () => void;
}

export function ProcessingStatusTimeline({ file, onRefresh }: ProcessingStatusTimelineProps) {
  const [startTime] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  const isProcessing = file.status === "uploaded" || file.status === "processing";
  const isDone = !isProcessing;
  const isFailed = file.status === "validation_failed";

  useEffect(() => {
    if (!isProcessing) return;
    const timer = setInterval(() => setElapsed(Date.now() - startTime), 1000);
    return () => clearInterval(timer);
  }, [isProcessing, startTime]);

  const processingDuration = useMemo(() => {
    if (file.processingCompletedAt) {
      const completed = new Date(file.processingCompletedAt).getTime();
      const started = new Date(file.uploadedAt).getTime();
      return completed - started;
    }
    return isProcessing ? elapsed : 0;
  }, [file.processingCompletedAt, file.uploadedAt, elapsed, isProcessing]);

  const stageOrder = KNOWN_STAGES.filter((s) => s !== "Extraction Complete");
  const currentStage = file.processingStage || "Initializing";

  const stageStatuses = useMemo(
    () => stageOrder.map((stage) => ({ stage, status: getStageStatus(stage, currentStage, file.status) })),
    [stageOrder, currentStage, file.status],
  );

  const completedStages = stageStatuses.filter((s) => s.status === "completed").length;
  const activeStage = stageStatuses.find((s) => s.status === "active");
  const totalStages = stageOrder.length;

  const errorLog = useMemo(() => {
    if (!isFailed) return null;
    return (file.processingLogs || []).find((log) => log.status === "failed");
  }, [isFailed, file.processingLogs]);

  return (
    <div className="space-y-6">
      {/* Header summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {isDone ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                ) : (
                  <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                )}
                  {isDone ? "Processing completed" : "Processing in progress"}
              </CardTitle>
              <CardDescription>
                {isDone
                  ? "All pipeline stages finished successfully."
                  : "Running document pipeline — this page updates automatically."}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {!isDone && onRefresh && (
                <Button variant="outline" size="sm" onClick={onRefresh}>
                  <Loader2 className="mr-1.5 h-4 w-4" />Refresh
                </Button>
              )}
              <Badge variant={isFailed ? "danger" : isDone ? "success" : "info"}>
                {isFailed ? "Failed" : isDone ? "Completed" : "Running"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500">File name</span>
              <p className="mt-1 truncate font-semibold">{file.fileName}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500">Current stage</span>
              <p className="mt-1 font-semibold">{currentStage}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500">Pipeline progress</span>
              <p className="mt-1 font-semibold tabular-nums">
                {completedStages} of {totalStages} stages
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
              <span className="text-xs font-medium text-slate-500">Elapsed time</span>
              <p className="mt-1 font-semibold tabular-nums">
                {formatDuration(processingDuration)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress bar */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline progress</CardTitle>
        </CardHeader>
        <CardContent>
          <Progress value={(completedStages / totalStages) * 100} className="h-3" />
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>{Math.round((completedStages / totalStages) * 100)}% complete</span>
            <span>{activeStage ? `Current: ${activeStage.stage}` : isDone ? "All stages complete" : ""}</span>
          </div>
        </CardContent>
      </Card>

      {/* Live timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Processing timeline</CardTitle>
          <CardDescription>Real pipeline stages from the backend processing engine.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            {stageStatuses.map(({ stage, status }, index) => (
              <div key={stage} className="relative flex gap-4 pb-6 last:pb-0">
                {index < stageStatuses.length - 1 ? (
                  <div
                    className={cn(
                      "absolute left-[9px] top-5 h-full w-0.5",
                      status === "completed" ? "bg-emerald-300 dark:bg-emerald-700" : "bg-slate-200 dark:bg-slate-800",
                    )}
                  />
                ) : null}
                <div className="z-10 flex h-5 w-5 items-center justify-center">
                  <StageIcon status={status} />
                </div>
                <div className="flex-1 pt-0.5">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      status === "completed" && "text-emerald-700 dark:text-emerald-300",
                      status === "active" && "text-blue-700 dark:text-blue-300",
                      status === "failed" && "text-red-700 dark:text-red-300",
                      status === "pending" && "text-slate-400 dark:text-slate-500",
                    )}
                  >
                    {stage}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Error display */}
      {isFailed && errorLog && (
        <Card className="border-red-200 dark:border-red-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              {errorLog.step} failed
            </CardTitle>
            <CardDescription className="text-red-500">{errorLog.message}</CardDescription>
          </CardHeader>
          <CardContent>
            {errorLog.errorDetails && (
              <div className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">
                <span className="font-medium">Reason:</span> {errorLog.errorDetails}
              </div>
            )}
            <p className="mb-4 text-sm text-slate-500">Action: Review the error and retry processing.</p>
            <div className="flex gap-2">
              <Button variant="outline" asChild>
                <Link to={`/app/files/${file.id}`}>
                  <Eye className="mr-1.5 h-4 w-4" />View Logs
                </Link>
              </Button>
              <Button
                variant="default"
                onClick={async () => {
                  try {
                    await fileApi.retryProcessingStep(file.id, "Processing");
                    window.location.reload();
                  } catch {
                    window.location.reload();
                  }
                }}
              >
                <Loader2 className="mr-1.5 h-4 w-4" />Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completion state */}
      {isDone && !isFailed && file.extractionJson && (
        <Card className="border-emerald-200 dark:border-emerald-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
              Processing completed successfully
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Document type</span>
                <p className="mt-1 font-semibold capitalize">{file.extractionJson.document_type || "—"}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Fields extracted</span>
                <p className="mt-1 font-semibold tabular-nums">
                  {file.extractionJson.processing_metrics?.fields_extracted ?? file.extractionJson.confidence_details?.length ?? 0}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Tables extracted</span>
                <p className="mt-1 font-semibold tabular-nums">
                  {file.extractionJson.processing_metrics?.tables_extracted ?? 0}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">OCR confidence</span>
                <p className="mt-1 font-semibold tabular-nums">
                  {file.extractionJson.overall_confidence != null ? `${Math.round(file.extractionJson.overall_confidence * 100)}%` : "—"}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Processing engine</span>
                <p className="mt-1 font-semibold tabular-nums">{file.extractionJson.ocr_engine || "—"}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Preprocessing</span>
                <p className="mt-1 font-semibold tabular-nums">
                  {file.extractionJson.processing_metrics?.preprocessing_applied ? "Applied" : "N/A"}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Pages</span>
                <p className="mt-1 font-semibold tabular-nums">
                  {file.extractionJson.metadata?.page_count ?? "—"}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Processing time</span>
                <p className="mt-1 font-semibold tabular-nums">{formatDuration(processingDuration)}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="default" asChild>
                <Link to={`/app/files/${file.id}`}>
                  <Eye className="mr-1.5 h-4 w-4" />View Extracted Fields
                </Link>
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  fileApi.downloadExtractionJson(file.id, `extraction_${file.id.slice(0, 8)}.json`)
                    .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
                }}
              >
                <Code2 className="mr-1.5 h-4 w-4" />Download JSON
              </Button>
              <Button variant="outline" asChild>
                <Link to={`/app/files/${file.id}`}>
                  <FileText className="mr-1.5 h-4 w-4" />Preview Document
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to={`/app/files/${file.id}`}>
                  <Download className="mr-1.5 h-4 w-4" />View Processing Logs
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completed but no extraction JSON (partial/simple docs) */}
      {isDone && !isFailed && !file.extractionJson && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
              Processing completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Status</span>
                <p className="mt-1 font-semibold capitalize">{file.status.replace("_", " ")}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Confidence</span>
                <ConfidenceBar label="" value={file.confidence} compact />
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900">
                <span className="text-xs font-medium text-slate-500">Processing time</span>
                <p className="mt-1 font-semibold tabular-nums">{formatDuration(processingDuration)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
