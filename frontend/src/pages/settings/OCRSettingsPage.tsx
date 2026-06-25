import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import type { OcrSettings } from "@/types";
import { ocrSettingsSchema } from "@/schemas/settings.schema";
import { settingsApi } from "@/services/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { SettingsFormActions } from "@/components/settings/SettingsFormActions";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/useToast";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";

const engines = ["Mistral OCR", "PaddleOCR", "Azure Document Intelligence", "AWS Textract", "Google Document AI"] as const;

export function OCRSettingsPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["settings", "ocr"], queryFn: settingsApi.getOcrSettings });
  const form = useForm<OcrSettings>({ resolver: zodResolver(ocrSettingsSchema), defaultValues: query.data });
  useEffect(() => { if (query.data) form.reset(query.data); }, [form, query.data]);
  useUnsavedChanges(form.formState.isDirty);
  const save = useMutation({ mutationFn: settingsApi.saveOcrSettings, onSuccess: (data) => { form.reset(data); toast.success("Document processing settings saved", "New files will use the updated document-processing policy."); }, onError: (error) => toast.error("Unable to save document processing settings", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading document processing settings..." />;
  if (query.isError) return <ErrorState title="Document processing settings unavailable" description="Document processing configuration could not be loaded." onRetry={() => query.refetch()} />;
  return <form className="space-y-6" onSubmit={form.handleSubmit((value) => save.mutate(value))}>
    <PageHeader eyebrow="Phase 12 · Administration" title="Document processing" description="Configure OCR engines, cloud fallback, confidence thresholds, table extraction, layout analysis, and handwriting recognition." actions={<Badge variant="success">PaddleOCR default</Badge>} />
    <Card><CardHeader><CardTitle>Engine policy</CardTitle><CardDescription>Primary and fallback engines are tenant-scoped and applied to newly ingested files.</CardDescription></CardHeader><CardContent className="grid gap-5 md:grid-cols-2">
      <div className="space-y-2"><Label>Primary OCR engine</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" {...form.register("primaryEngine")}>{engines.map((engine) => <option key={engine}>{engine}</option>)}</select></div>
      <div className="space-y-2"><Label>Cloud fallback engine</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" {...form.register("fallbackEngine")}>{engines.filter((engine) => engine !== "PaddleOCR").map((engine) => <option key={engine}>{engine}</option>)}</select></div>
      <div className="space-y-2"><Label>OCR confidence threshold (%)</Label><Input type="number" {...form.register("confidenceThreshold")} /></div>
      <div className="space-y-2"><Label>Maximum pages per file</Label><Input type="number" {...form.register("maxPagesPerFile")} /></div>
    </CardContent></Card>
    <Card><CardHeader><CardTitle>Extraction capabilities</CardTitle><CardDescription>Enable only the features needed by your document mix.</CardDescription></CardHeader><CardContent className="grid gap-4 md:grid-cols-2">
      <Controller control={form.control} name="cloudFallbackEnabled" render={({ field }) => <Switch label="Enable cloud OCR fallback" checked={field.value} onCheckedChange={field.onChange} />} />
      <Controller control={form.control} name="tableExtractionEnabled" render={({ field }) => <Switch label="Enable table extraction" checked={field.value} onCheckedChange={field.onChange} />} />
      <Controller control={form.control} name="layoutAnalysisEnabled" render={({ field }) => <Switch label="Enable layout analysis" checked={field.value} onCheckedChange={field.onChange} />} />
      <Controller control={form.control} name="handwritingEnabled" render={({ field }) => <Switch label="Enable handwriting recognition" checked={field.value} onCheckedChange={field.onChange} />} />
    </CardContent></Card>
    <SettingsFormActions dirty={form.formState.isDirty} saving={save.isPending} onCancel={() => form.reset(query.data)} />
  </form>;
}
