import { useState, useCallback, useRef, useEffect, type ComponentType } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  FileText,
  FileUp,
  Layers3,
  ListChecks,
  Loader2,
  ScanLine,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  Sparkles,
  Zap,
} from "lucide-react";
import { ingestionApi } from "@/services/ingestionApi";
import { fileApi } from "@/services/fileApi";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { DocumentRegistryTable } from "@/components/files/DocumentRegistryTable";
import { OriginalFilePreview } from "@/components/files/OriginalFilePreview";
import { ExtractionJsonViewer } from "@/components/files/ExtractionJsonViewer";
import { formatDateTime } from "@/utils/formatters";

type StepState = "pending" | "active" | "completed" | "failed" | "skipped";

interface StepVisual {
  containerClass: string;
  iconClass: string;
  titleClass: string;
  descriptionClass: string;
}

const STEP_VISUALS: Record<StepState, StepVisual> = {
  pending: {
    containerClass: "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900",
    iconClass: "text-slate-400 dark:text-slate-600",
    titleClass: "text-slate-600 dark:text-slate-300",
    descriptionClass: "text-slate-400 dark:text-slate-500",
  },
  active: {
    containerClass: "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/40",
    iconClass: "text-amber-600 dark:text-amber-400 animate-spin",
    titleClass: "text-amber-800 dark:text-amber-300",
    descriptionClass: "text-amber-600 dark:text-amber-400",
  },
  completed: {
    containerClass: "border-emerald-200 bg-emerald-50 dark:border-emerald-900/60 dark:bg-emerald-950/40",
    iconClass: "text-emerald-600 dark:text-emerald-400",
    titleClass: "text-emerald-800 dark:text-emerald-300",
    descriptionClass: "text-emerald-600 dark:text-emerald-400",
  },
  failed: {
    containerClass: "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/40",
    iconClass: "text-red-600 dark:text-red-400",
    titleClass: "text-red-700 dark:text-red-300",
    descriptionClass: "text-red-500 dark:text-red-400",
  },
  skipped: {
    containerClass: "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900",
    iconClass: "text-slate-300 dark:text-slate-700",
    titleClass: "text-slate-400 dark:text-slate-600",
    descriptionClass: "text-slate-400 dark:text-slate-600",
  },
};

const STEP_STATE_ICON: Record<StepState, ComponentType<{ className?: string }>> = {
  pending: Clock,
  active: Loader2,
  completed: CheckCircle2,
  failed: AlertCircle,
  skipped: Clock,
};

interface PipelineStep {
  key: string;
  icon: ComponentType<{ className?: string }>;
  title: string;
  description: string;
  state: StepState;
}

function PipelineStepCard({ step }: { step: PipelineStep }) {
  const visual = STEP_VISUALS[step.state];
  const StepIcon = step.icon;
  const StateIcon = STEP_STATE_ICON[step.state];
  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 ${visual.containerClass}`}>
      <StepIcon className={`mt-0.5 h-5 w-5 shrink-0 ${visual.iconClass.replace(" animate-spin", "")}`} />
      <div className="flex-1 text-sm">
        <div className="flex items-center gap-1.5">
          <p className={`font-medium ${visual.titleClass}`}>{step.title}</p>
          <StateIcon className={`h-3.5 w-3.5 shrink-0 ${visual.iconClass}`} />
        </div>
        <p className={`text-xs ${visual.descriptionClass}`}>{step.description}</p>
      </div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
      <div className="mt-0.5 text-sm font-medium text-slate-800 dark:text-slate-200">{value ?? <span className="text-slate-400 dark:text-slate-600">{'—'}</span>}</div>
    </div>
  );
}

export function DocumentExtractionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fileId = searchParams.get("fileId");
  const registryId = searchParams.get("registryId");
  const [preparingExtraction, setPreparingExtraction] = useState(false);
  const [autoPrepareAttempted, setAutoPrepareAttempted] = useState(false);
  const queryClient = useQueryClient();
  const previousDocStatus = useRef<string | null>(null);
  const previousEntryStatus = useRef<string | null>(null);

  // Fetch the intake registry entry for context
  const entryQuery = useQuery({
    queryKey: ["intake-entry", registryId],
    queryFn: () => ingestionApi.getIntakeEntry(registryId!),
    enabled: !!registryId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      const inProgress = !["extracted", "failed"].includes(data.status);
      return inProgress ? 3000 : false;
    },
  });

  // Fetch the workspace file for extraction results
  const fileQuery = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => fileApi.getFile(fileId!),
    enabled: !!fileId,
    retry: 3,
    retryDelay: 2000,
    refetchInterval: (query) => {
      if (query.state.status === "error") return false;
      const data = query.state.data;
      if (!data) return 2000;
      return data.status === "uploaded" || data.status === "processing" ? 2000 : false;
    },
  });

  // Auto-trigger extraction preparation when page loads with only a registryId
  const prepareMutation = useMutation({
    mutationFn: (entryId: string) => ingestionApi.prepareExtraction(entryId),
    onSuccess: (result) => {
      setPreparingExtraction(false);
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
      queryClient.invalidateQueries({ queryKey: ["document-registry"] });
      // Navigate to the proper URL with fileId
      navigate(result.redirect_url, { replace: true });
    },
    onError: (err: Error) => {
      setPreparingExtraction(false);
    },
  });

  // Auto-prepare extraction when:
  // 1. We have a registryId but no fileId, OR
  // 2. File query failed and we haven't tried auto-preparing yet
  useEffect(() => {
    if (autoPrepareAttempted) return;
    if (preparingExtraction) return;

    const shouldAutoPrepare =
      (registryId && !fileId && entryQuery.data?.status === "ready_for_extraction") ||
      (fileQuery.isError && registryId && !fileId && entryQuery.isFetched);

    if (shouldAutoPrepare && !prepareMutation.isPending) {
      setAutoPrepareAttempted(true);
      setPreparingExtraction(true);
      prepareMutation.mutate(registryId);
    }
  }, [registryId, fileId, fileQuery.isError, entryQuery.data, entryQuery.isFetched, autoPrepareAttempted, preparingExtraction, prepareMutation]);

  const doc = fileQuery.data;
  const entry = entryQuery.data;
  const hasContext = Boolean(fileId || registryId);

  useEffect(() => {
    if (!doc?.status) return;
    if (previousDocStatus.current === doc.status) return;
    previousDocStatus.current = doc.status;
    queryClient.invalidateQueries({ queryKey: ["document-registry"] });
  }, [doc?.status, queryClient]);

  useEffect(() => {
    if (!entry?.status) return;
    if (previousEntryStatus.current === entry.status) return;
    previousEntryStatus.current = entry.status;
    queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
  }, [entry?.status, queryClient]);

  const handleBack = () => navigate("/app/ingestion/data-ingestion");

  const PIPELINE_STAGES: { key: string; icon: ComponentType<{ className?: string }>; title: string }[] = [
    { key: "uploaded", icon: FileUp, title: "Document Uploaded" },
    { key: "preprocessing", icon: Layers3, title: "Preprocessing" },
    { key: "document_analysis", icon: ScanLine, title: "Document Analysis" },
    { key: "mistral_processing", icon: Sparkles, title: "Mistral OCR Processing" },
    { key: "field_extraction", icon: ListChecks, title: "Field Extraction" },
    { key: "validation", icon: ShieldCheck, title: "Validation" },
    { key: "complete", icon: CheckCircle2, title: "Extraction Complete" },
  ];

  function stageIndexFromProcessingStage(stage: string | undefined): number {
    switch (stage) {
      case "Preprocessing": return 1;
      case "Document Analysis": return 2;
      case "Mistral OCR Processing": return 3;
      case "Field Extraction": return 4;
      case "Validation": return 5;
      case "Extraction Complete": return 6;
      default: return 0;
    }
  }

  const isFailed = doc?.status === "validation_failed";
  const isDocComplete = doc?.status === "completed" || doc?.status === "needs_review";
  const currentStageIndex = doc
    ? isDocComplete
      ? 6
      : isFailed
        ? Math.max(1, stageIndexFromProcessingStage(doc.processingStage))
        : stageIndexFromProcessingStage(doc.processingStage)
    : 0;

  function stageDescription(idx: number): string {
    if (!doc) return "";
    const progress = doc.extractionProgress;
    const isStageFailed = progress?.currentStage === "extraction_failed" && isFailed;
    switch (idx) {
      case 0:
        return `Received ${formatDateTime(doc.uploadedAt)}.`;
      case 1:
        return isStageFailed ? (progress?.error ?? "Preprocessing failed.") : "Validating the file and preparing it for analysis.";
      case 2:
        return isStageFailed ? (progress?.error ?? "Document analysis failed.") : "Reading document structure, pages, and content.";
      case 3: {
        if (isStageFailed) return progress?.error ?? "Extraction failed.";
        if (progress && progress.totalChunks > 1) {
          const pct = progress.progressPct ?? Math.round((progress.completedChunks / progress.totalChunks) * 100);
          return `Extracting ${progress.totalPages} pages in ${progress.totalChunks} chunks · ${progress.completedChunks}/${progress.totalChunks} chunks done (${pct}%)${progress.currentChunk ? ` · last completed: ${progress.currentChunk}` : ""}.`;
        }
        return doc.extractionConfidence != null
          ? `Mistral OCR analysis · ${Math.round(doc.extractionConfidence * 100)}% confidence.`
          : "Mistral OCR is processing the document.";
      }
      case 4: {
        if (isStageFailed) return progress?.error ?? "Field extraction failed.";
        if (progress?.currentStage === "merging" && progress.totalChunks > 1) {
          return `Merging results from ${progress.totalChunks} chunks into one structured output.`;
        }
        return doc.extractionJson
          ? `${doc.extractionJson.confidence_details?.length ?? 0} field(s) mapped from OCR response.`
          : "Mapping OCR response onto structured fields.";
      }
      case 5:
        if (isStageFailed) return progress?.error ?? "Validation failed.";
        return doc.extractionJson?.validation_results?.length
          ? `${doc.extractionJson.validation_results.length} validation check(s) run.`
          : "Running business rule and consistency checks.";
      case 6:
        return doc.status === "needs_review"
          ? "Complete — some fields need manual review."
          : doc.status === "completed"
            ? "Complete — all fields extracted successfully."
            : "Finalizing extraction.";
      default:
        return "";
    }
  }

  const pipelineSteps: PipelineStep[] = doc
    ? PIPELINE_STAGES.map(({ key, icon, title }, idx) => {
        let state: StepState;
        if (isFailed && idx === currentStageIndex) state = "failed";
        else if (isFailed && idx > currentStageIndex) state = "pending";
        else if (idx < currentStageIndex) state = "completed";
        else if (isDocComplete) state = "completed";
        else if (idx === currentStageIndex) state = "active";
        else state = "pending";
        return { key, icon, title, state, description: stageDescription(idx) };
      })
    : [];

  // Show preparing extraction overlay when extraction is being set up
  if (preparingExtraction || prepareMutation.isPending) {
    return (
      <>
        <PageHeader
          eyebrow="Document Extraction"
          title="Starting Extraction..."
          description="Setting up the Mistral OCR extraction pipeline"
          actions={
            <Button variant="outline" onClick={handleBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Intake
            </Button>
          }
        />
        <div className="flex flex-col items-center justify-center py-20">
          <div className="relative mb-6 h-20 w-20">
            <Loader2 className="h-20 w-20 animate-spin text-emerald-500" />
            <Sparkles className="absolute left-1/2 top-1/2 h-8 w-8 -translate-x-1/2 -translate-y-1/2 text-emerald-600" />
          </div>
          <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">Preparing extraction pipeline...</p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Mistral OCR is being initialized for document processing.
          </p>
          {entry && (
            <div className="mt-6 flex items-center gap-2 text-sm text-slate-400">
              <FileText className="h-4 w-4" />
              {entry.original_filename}
            </div>
          )}
          <div className="mt-8 grid grid-cols-4 gap-3">
            {["Preprocessing", "OCR", "Layout Analysis", "Extraction"].map((step, i) => (
              <div
                key={step}
                className="flex animate-pulse items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900"
              >
                <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Document Extraction"
        title={doc?.fileName ?? entry?.original_filename ?? "Document Extraction"}
        description={
          doc
            ? `Extraction results for "${doc.fileName}"`
            : entry
              ? `Extraction pipeline for "${entry.original_filename}"`
              : "Extraction workflow"
        }
        actions={
          <Button variant="outline" onClick={handleBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Intake
          </Button>
        }
      />

      {!hasContext ? (
        <>
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="mb-3 h-10 w-10 text-slate-300 dark:text-slate-700" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">No document selected</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 mb-4">
                Navigate from the Data Intake registry to start extraction.
              </p>
              <Button onClick={handleBack}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go to Intake Registry
              </Button>
            </CardContent>
          </Card>
          <div className="mt-6">
            <DocumentRegistryTable />
          </div>
        </>
      ) : fileQuery.isLoading || (!doc && entryQuery.isLoading) ? (
        <LoadingState label="Loading extraction results..." />
      ) : fileQuery.isError && !doc ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="mb-4 h-12 w-12 text-amber-500" />
            <p className="text-base font-semibold text-slate-700 dark:text-slate-300">Extraction pipeline starting</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 max-w-md">
              The document is being queued for Mistral OCR extraction. This page will refresh automatically when ready.
            </p>
            {entry && (
              <div className="mt-6 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm dark:border-slate-800 dark:bg-slate-900">
                <Clock className="h-4 w-4 text-slate-400" />
                <span className="text-slate-600 dark:text-slate-400">Status: {entry.status.replace(/_/g, " ")}</span>
                <Loader2 className="ml-2 h-3.5 w-3.5 animate-spin text-amber-500" />
              </div>
            )}
            {!entry && (
              <Button
                variant="outline"
                className="mt-6"
                onClick={() => fileQuery.refetch()}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Check Again
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* 1. Document Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-slate-400" />
                Document Information
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <InfoField label="File Name" value={doc?.fileName ?? entry?.original_filename} />
              <InfoField label="Document Type" value={doc?.extractionJson?.document_type ?? entry?.document_type ?? doc?.type} />
              <InfoField label="Upload Date" value={formatDateTime(doc?.uploadedAt ?? entry?.created_at ?? "")} />
              <InfoField label="Extraction Status" value={doc ? <StatusBadge status={doc.status} /> : entry ? <StatusBadge status={entry.status} /> : undefined} />
              <InfoField label="Document ID" value={<code className="font-mono text-xs">{doc?.id ?? entry?.id}</code>} />
            </CardContent>
          </Card>

          {/* 2. Document Preview */}
          {doc ? (
            <OriginalFilePreview file={doc} />
          ) : (
            <Card>
              <CardContent className="py-10">
                <LoadingState label="Preparing document preview..." />
              </CardContent>
            </Card>
          )}

          {/* Extraction error banner */}
          {isFailed && doc?.extractionProgress?.error && (() => {
            const errMsg = doc.extractionProgress!.error!;
            const isBilling = errMsg.toLowerCase().includes("prepayment") || errMsg.toLowerCase().includes("credits are depleted");
            const isAuth = errMsg.toLowerCase().includes("authentication failed");
            return (
              <div className={`rounded-lg border p-4 ${isBilling ? "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/40" : "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/40"}`}>
                <div className="flex gap-3">
                  <AlertCircle className={`h-5 w-5 flex-shrink-0 mt-0.5 ${isBilling ? "text-amber-500" : "text-red-500"}`} />
                  <div className="min-w-0">
                    <p className={`font-semibold ${isBilling ? "text-amber-800 dark:text-amber-300" : "text-red-800 dark:text-red-300"}`}>
                      {isBilling ? "API Billing Required" : isAuth ? "API Authentication Failed" : "Extraction Failed"}
                    </p>
                    <p className={`mt-1 text-sm ${isBilling ? "text-amber-700 dark:text-amber-400" : "text-red-600 dark:text-red-400"}`}>
                      {errMsg}
                    </p>
                    {isBilling && (
                      <a
                        href="https://aistudio.google.com/apikey"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-block text-sm font-medium text-amber-800 underline dark:text-amber-300"
                      >
                        Manage billing →
                      </a>
                    )}
                    {isAuth && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        Check that <code className="font-mono text-xs">MISTRAL_API_KEY</code> is set correctly in your <code className="font-mono text-xs">.env</code> file.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          {/* 3. Processing Pipeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-emerald-500" />
                Processing Pipeline
              </CardTitle>
              <CardDescription>
                Live status across every stage of the extraction pipeline.
                {doc && (doc.status === "uploaded" || doc.status === "processing") && (
                  <span className="ml-2 inline-flex items-center gap-1 text-amber-600">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Processing...
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {pipelineSteps.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {pipelineSteps.map((step) => (
                    <PipelineStepCard key={step.key} step={step} />
                  ))}
                </div>
              ) : (
                <LoadingState label="Preparing pipeline status..." />
              )}
              {/* Pipeline progress bar */}
              {doc && (doc.status === "uploaded" || doc.status === "processing") && (
                <div className="mt-4">
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-amber-400 via-emerald-400 to-blue-500 transition-all duration-700"
                      style={{
                        width: `${
                          pipelineSteps.filter((s) => s.state === "completed").length /
                          pipelineSteps.length *
                          100
                        }%`,
                      }}
                    />
                  </div>
                  <p className="mt-2 text-right text-xs text-slate-400">
                    {pipelineSteps.filter((s) => s.state === "completed").length} of {pipelineSteps.length} stages complete
                  </p>
                </div>
              )}
              {/* Multi-page chunk extraction progress — only shown for documents
                  large enough to require chunked processing. */}
              {doc?.extractionProgress && doc.extractionProgress.totalChunks > 1 && (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
                  <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-slate-500 dark:text-slate-400">
                    <span>
                      {doc.extractionProgress.totalPages} pages · {doc.extractionProgress.totalChunks} chunks
                      {doc.extractionProgress.currentStage === "extracting" ? " (extracting in parallel)" : ""}
                      {doc.extractionProgress.currentStage === "merging" ? " (merging results)" : ""}
                      {doc.extractionProgress.currentStage === "validating" ? " (validating)" : ""}
                    </span>
                    <span>
                      {doc.extractionProgress.completedChunks}/{doc.extractionProgress.totalChunks} chunks
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                      style={{
                        width: `${(doc.extractionProgress.completedChunks / doc.extractionProgress.totalChunks) * 100}%`,
                      }}
                    />
                  </div>
                  {(doc.extractionProgress.pagesPerSec != null || doc.extractionProgress.etaSeconds != null) && (
                    <div className="mt-1.5 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                      {doc.extractionProgress.pagesPerSec != null && (
                        <span>{doc.extractionProgress.pagesPerSec} pages/sec</span>
                      )}
                      {doc.extractionProgress.etaSeconds != null && doc.extractionProgress.etaSeconds > 0 && (
                        <span>ETA {doc.extractionProgress.etaSeconds < 60
                          ? `${doc.extractionProgress.etaSeconds}s`
                          : `${Math.floor(doc.extractionProgress.etaSeconds / 60)}m ${doc.extractionProgress.etaSeconds % 60}s`}
                        </span>
                      )}
                    </div>
                  )}
                  {doc.extractionProgress.failedChunks && doc.extractionProgress.failedChunks.length > 0 && (
                    <p className="mt-1.5 text-xs text-amber-600">
                      {doc.extractionProgress.failedChunks.length} chunk(s) failed after retries: {doc.extractionProgress.failedChunks.map((c) => c.pages).join(", ")}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 4. Extracted Fields / JSON Viewer */}
          <ExtractionJsonViewer json={doc?.extractionJson ?? null} loading={fileQuery.isLoading} fileId={doc?.id} />

          {/* 5. Document Registry */}
          <div className="pt-2">
            <h2 className="mb-3 text-base font-semibold text-slate-700 dark:text-slate-300">Document Registry</h2>
            <DocumentRegistryTable />
          </div>
        </div>
      )}
    </>
  );
}
