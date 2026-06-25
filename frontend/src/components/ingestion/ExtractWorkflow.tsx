import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSearch,
  Loader2,
  RefreshCw,
  ScanLine,
  Table2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { DocumentPreview } from "./DocumentPreview";
import { ExtractedFieldsTable } from "./ExtractedFieldsTable";
import { ingestionApi } from "@/services/ingestionApi";
import type {
  ExtractedField,
  ExtractionResult,
  PreprocessingResult,
  DedupResult,
} from "@/types";

type WorkflowStep = "idle" | "preprocessing" | "deduplication" | "extracting" | "completed" | "failed";

interface ExtractWorkflowProps {
  fileId: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  onExportJson?: (jsonString: string) => void;
}

export function ExtractWorkflow({
  fileId,
  filename,
  contentType,
  sizeBytes,
  onExportJson,
}: ExtractWorkflowProps) {
  const [step, setStep] = useState<WorkflowStep>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [preprocessingResult, setPreprocessingResult] = useState<PreprocessingResult | null>(null);
  const [dedupResult, setDedupResult] = useState<DedupResult | null>(null);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);

  const reset = () => {
    setStep("idle");
    setProgress(0);
    setError(null);
    setPreprocessingResult(null);
    setDedupResult(null);
    setExtractionResult(null);
  };

  const runPreprocessing = async () => {
    setStep("preprocessing");
    setProgress(10);
    setError(null);
    try {
      const result = await ingestionApi.preprocessFile(fileId);
      setPreprocessingResult(result);
      setProgress(35);
      return result;
    } catch (err) {
      setStep("failed");
      setError(err instanceof Error ? err.message : "Preprocessing failed");
      throw err;
    }
  };

  const runDeduplication = async () => {
    setStep("deduplication");
    setProgress(40);
    try {
      const result = await ingestionApi.deduplicateFile(fileId);
      setDedupResult(result);
      setProgress(60);
      return result;
    } catch (err) {
      setStep("failed");
      setError(err instanceof Error ? err.message : "Deduplication failed");
      throw err;
    }
  };

  const runExtraction = async () => {
    setStep("extracting");
    setProgress(65);
    try {
      const response = await ingestionApi.extractFields(fileId);
      if (response.status === "failed" || response.error) {
        throw new Error(response.error ?? "Extraction failed");
      }
      if (!response.result) {
        throw new Error("No extraction result returned");
      }
      setExtractionResult(response.result);
      setProgress(100);
      setStep("completed");
    } catch (err) {
      setStep("failed");
      setError(err instanceof Error ? err.message : "Extraction failed");
      throw err;
    }
  };

  const runFullWorkflow = async () => {
    setProgress(0);
    try {
      await runPreprocessing();
      await runDeduplication();
      await runExtraction();
    } catch {
      // error already set in individual steps
    }
  };

  const handleExport = () => {
    if (!extractionResult) return;
    const payload = JSON.stringify(
      {
        fileId: extractionResult.fileId,
        filename: extractionResult.filename,
        extractedAt: new Date().toISOString(),
        confidence: extractionResult.confidence,
        ocrEngine: extractionResult.ocrEngine,
        fields: extractionResult.fields,
        rawText: extractionResult.rawText,
        metadata: preprocessingResult?.metadata ?? null,
      },
      null,
      2,
    );
    if (onExportJson) {
      onExportJson(payload);
    } else {
      const blob = new Blob([payload], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename.replace(/\.[^.]+$/, "")}_extracted.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }
  };

  const stepBadge = (current: WorkflowStep, target: WorkflowStep, label: string) => {
    const states: WorkflowStep[] = ["preprocessing", "deduplication", "extracting", "completed"];
    const currentIdx = states.indexOf(current);
    const targetIdx = states.indexOf(target);

    if (current === "failed") {
      return <Badge variant="danger">Failed</Badge>;
    }
    if (current === target && current !== "idle") {
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    }
    if (currentIdx > targetIdx || current === "completed") {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    }
    if (current === "idle" || currentIdx < targetIdx) {
      return <span className="h-4 w-4 rounded-full border-2 border-slate-300 dark:border-slate-600" />;
    }
    return <span className="h-4 w-4 rounded-full border-2 border-slate-300" />;
  };

  return (
    <div className="space-y-6">
      {/* Workflow Steps */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <ScanLine className="h-5 w-5 text-primary" />
              Extraction workflow
            </CardTitle>
            <div className="flex gap-2">
              {step === "completed" && (
                <Button variant="outline" size="sm" onClick={handleExport}>
                  <Download className="mr-1 h-4 w-4" />
                  Export JSON
                </Button>
              )}
              {(step === "completed" || step === "failed") && (
                <Button variant="ghost" size="sm" onClick={reset}>
                  <RefreshCw className="mr-1 h-4 w-4" />
                  Reset
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {step === "idle" ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-4 dark:bg-slate-900">
                <div className="rounded-full bg-primary/10 p-2">
                  <FileSearch className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Ready to process</p>
                  <p className="text-xs text-slate-500">
                    This will run preprocessing, deduplication, and field extraction.
                  </p>
                </div>
                <Button onClick={runFullWorkflow}>
                  <ScanLine className="mr-1 h-4 w-4" />
                  Start extraction
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <Progress value={progress} className="h-2" />

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  {stepBadge(step, "preprocessing", "Preprocessing")}
                  <div className="flex-1">
                    <p className="text-sm font-medium">Preprocessing &amp; data lake</p>
                    <p className="text-xs text-slate-500">
                      {step === "preprocessing"
                        ? "Generating metadata, parsing structure, storing in tiers..."
                        : preprocessingResult
                          ? `${(preprocessingResult.durationMs / 1000).toFixed(1)}s · ${preprocessingResult.metadata.pageCount} pages`
                          : "Pending"}
                    </p>
                  </div>
                  {preprocessingResult && (
                    <Badge variant="success" className="text-xs">
                      Done
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {stepBadge(step, "deduplication", "Deduplication")}
                  <div className="flex-1">
                    <p className="text-sm font-medium">Deduplication</p>
                    <p className="text-xs text-slate-500">
                      {dedupResult
                        ? dedupResult.isDuplicate
                          ? `Similarity ${(dedupResult.similarityScore * 100).toFixed(1)}% — potential duplicate`
                          : "No duplicates found"
                        : "Pending"}
                    </p>
                  </div>
                  {dedupResult && (
                    <Badge variant={dedupResult.isDuplicate ? "warning" : "success"} className="text-xs">
                      {dedupResult.isDuplicate ? "Flagged" : "Unique"}
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {stepBadge(step, "extracting", "Extraction")}
                  <div className="flex-1">
                    <p className="text-sm font-medium">Field extraction</p>
                    <p className="text-xs text-slate-500">
                      {extractionResult
                        ? `${extractionResult.fields.length} fields extracted at ${(extractionResult.confidence * 100).toFixed(1)}% confidence`
                        : "Pending"}
                    </p>
                  </div>
                  {extractionResult && (
                    <Badge variant="success" className="text-xs">
                      {extractionResult.fields.length} fields
                    </Badge>
                  )}
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
                  <XCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                  <Button variant="outline" size="sm" className="ml-auto" onClick={runFullWorkflow}>
                    <RefreshCw className="mr-1 h-4 w-4" />
                    Retry
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Document Preview */}
      <DocumentPreview
        fileId={fileId}
        filename={filename}
        contentType={contentType}
        sizeBytes={sizeBytes}
        metadata={preprocessingResult?.metadata}
      />

      {/* Dedup Warning */}
      {dedupResult?.isDuplicate && dedupResult.matches.length > 0 && (
        <Card className="border-amber-200 dark:border-amber-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5" />
              Duplicate detected
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dedupResult.matches.slice(0, 3).map((match) => (
                <div key={match.fileId} className="flex items-center justify-between rounded-lg bg-amber-50 p-3 text-sm dark:bg-amber-950">
                  <span className="font-medium">{match.filename}</span>
                  <Badge variant="warning">{(match.similarity * 100).toFixed(1)}% similar</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Extracted Fields */}
      {extractionResult && (
        <ExtractedFieldsTable
          fields={extractionResult.fields}
          confidence={extractionResult.confidence}
          processingTimeMs={extractionResult.processingTimeMs}
          ocrEngine={extractionResult.ocrEngine}
          rawText={extractionResult.rawText}
          onExportJson={handleExport}
        />
      )}
    </div>
  );
}
