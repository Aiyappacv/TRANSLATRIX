import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import type { ApprovalRulesSettings } from "@/types";
import { approvalRulesSchema } from "@/schemas/settings.schema";
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
import { roleLabels } from "@/utils/permissions";

export function ApprovalRulesPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["settings", "approval-rules"], queryFn: settingsApi.getApprovalRules });
  const form = useForm<ApprovalRulesSettings>({ resolver: zodResolver(approvalRulesSchema), defaultValues: query.data });
  useEffect(() => { if (query.data) form.reset(query.data); }, [form, query.data]);
  useUnsavedChanges(form.formState.isDirty);
  const save = useMutation({ mutationFn: settingsApi.saveApprovalRules, onSuccess: (data) => { form.reset(data); toast.success("Approval rules saved", "New review tasks will use the updated policy."); }, onError: (error) => toast.error("Unable to save approval rules", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading approval policy..." />;
  if (query.isError) return <ErrorState title="Approval rules unavailable" description="The tenant approval policy could not be loaded." onRetry={() => query.refetch()} />;
  return <form className="space-y-6" onSubmit={form.handleSubmit((value) => save.mutate(value))}>
    <PageHeader eyebrow="Phase 12 · Administration" title="Approval rules" description="Amount, confidence, failure, and category-based escalation policy." />
    <Card><CardHeader><CardTitle>Thresholds and escalation</CardTitle><CardDescription>Amounts use the tenant base currency.</CardDescription></CardHeader><CardContent className="grid gap-5 md:grid-cols-2">
      <div className="space-y-2"><Label>Approval required above</Label><Input type="number" {...form.register("approvalRequiredAbove")} /></div>
      <div className="space-y-2"><Label>Second approval above</Label><Input type="number" {...form.register("secondApprovalAbove")} />{form.formState.errors.secondApprovalAbove?.message ? <p className="text-xs text-red-600">{form.formState.errors.secondApprovalAbove.message}</p> : null}</div>
      <div className="space-y-2"><Label>Low-confidence threshold (%)</Label><Input type="number" {...form.register("confidenceThreshold")} /></div>
      <div className="space-y-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
        <Controller control={form.control} name="lowConfidenceRequiresReview" render={({ field }) => <Switch label="Low confidence requires review" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
        <Controller control={form.control} name="sapFailedRequiresAdminReview" render={({ field }) => <Switch label="SAP failure requires admin review" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
        <Controller control={form.control} name="categoryBasedApproval" render={({ field }) => <Switch label="Enable category-based approval" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
      </div>
    </CardContent></Card>
    <Card><CardHeader><CardTitle>Category-based approval</CardTitle><CardDescription>Specialized role routing for financial risk categories.</CardDescription></CardHeader><CardContent className="space-y-3">{form.watch("categoryRules")?.map((rule, index) => <div key={rule.id} className="grid items-center gap-3 rounded-2xl border border-slate-200 p-4 md:grid-cols-[1fr_1fr_1fr_auto] dark:border-slate-800"><div><p className="font-semibold">{rule.category}</p><Badge variant="neutral">{roleLabels[rule.approverRole]}</Badge></div><Input type="number" aria-label={`${rule.category} threshold`} {...form.register(`categoryRules.${index}.threshold`)} /><select className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" {...form.register(`categoryRules.${index}.approverRole`)}>{Object.entries(roleLabels).filter(([role]) => !["spectra_super_admin", "read_only"].includes(role)).map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select><Controller control={form.control} name={`categoryRules.${index}.active`} render={({ field }) => <Switch checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} /></div>)}</CardContent></Card>
    <SettingsFormActions dirty={form.formState.isDirty} saving={save.isPending} onCancel={() => form.reset(query.data)} />
  </form>;
}
