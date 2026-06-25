import { useState } from "react";
import { ChevronDown, ChevronUp, Copy, Download, Eye, EyeOff, Table2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { EmptyState } from "@/components/common/EmptyState";
import type { ExtractedField } from "@/types";

interface ExtractedFieldsTableProps {
  fields: ExtractedField[];
  confidence: number;
  processingTimeMs: number;
  ocrEngine: string;
  rawText?: string;
  onExportJson?: () => void;
}

export function ExtractedFieldsTable({
  fields,
  confidence,
  processingTimeMs,
  ocrEngine,
  rawText,
  onExportJson,
}: ExtractedFieldsTableProps) {
  const [showRaw, setShowRaw] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const copyFields = async () => {
    const json = JSON.stringify(fields, null, 2);
    await navigator.clipboard.writeText(json);
  };

  if (fields.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Table2 className="h-5 w-5 text-primary" />
            Extracted fields
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No fields extracted"
            description="This document did not yield any structured fields. Try re-running extraction or check OCR results."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Table2 className="h-5 w-5 text-primary" />
              Extracted fields
              <Badge variant="neutral" className="ml-1 text-xs">
                {fields.length} field{fields.length === 1 ? "" : "s"}
              </Badge>
            </CardTitle>
            <div className="mt-1 space-y-1">
              <ConfidenceBar label="Overall confidence" value={confidence} />
              <p className="text-xs text-slate-500">
                {ocrEngine} &middot; {(processingTimeMs / 1000).toFixed(1)}s
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowRaw(!showRaw)}>
              {showRaw ? <EyeOff className="mr-1 h-4 w-4" /> : <Eye className="mr-1 h-4 w-4" />}
              {showRaw ? "Hide raw" : "Raw text"}
            </Button>
            <Button variant="outline" size="sm" onClick={copyFields}>
              <Copy className="mr-1 h-4 w-4" />
              Copy
            </Button>
            {onExportJson && (
              <Button variant="outline" size="sm" onClick={onExportJson}>
                <Download className="mr-1 h-4 w-4" />
                Export JSON
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <button
          type="button"
          className="flex w-full items-center justify-between rounded-lg bg-slate-50 px-4 py-2 text-sm font-medium dark:bg-slate-900"
          onClick={() => setExpanded(!expanded)}
        >
          <span>Structured fields</span>
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {expanded && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-600 dark:text-slate-400">Field</th>
                  <th className="px-4 py-2 font-semibold text-slate-600 dark:text-slate-400">Value</th>
                  <th className="px-4 py-2 font-semibold text-slate-600 dark:text-slate-400">Confidence</th>
                  <th className="px-4 py-2 font-semibold text-slate-600 dark:text-slate-400">Page</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {fields.map((field, i) => (
                  <tr key={`${field.name}-${i}`} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                    <td className="whitespace-nowrap px-4 py-2 font-medium capitalize">{field.name.replace(/_/g, " ")}</td>
                    <td className="max-w-[300px] truncate px-4 py-2 text-slate-700 dark:text-slate-300" title={String(field.value)}>
                      {String(field.value)}
                    </td>
                    <td className="px-4 py-2">
                      <Badge variant={field.confidence >= 0.85 ? "success" : field.confidence >= 0.6 ? "warning" : "danger"}>
                        {Math.round(field.confidence * 100)}%
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-slate-500">{field.pageNumber ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showRaw && rawText && (
          <div>
            <h4 className="mb-2 text-sm font-semibold text-slate-600 dark:text-slate-400">Raw OCR text</h4>
            <pre className="max-h-[300px] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-950">
              {rawText.slice(0, 20000)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
