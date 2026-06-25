import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import type { CompanySettingsForm } from "@/types";
import { companySettingsSchema } from "@/schemas/settings.schema";
import { settingsApi } from "@/services/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { SettingsFormActions } from "@/components/settings/SettingsFormActions";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/useToast";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";

const fields: Array<{ key: keyof CompanySettingsForm; label: string; type?: string }> = [
  { key: "legalName", label: "Company legal name" }, { key: "tradingName", label: "Trading name" },
  { key: "country", label: "Country" }, { key: "industry", label: "Industry" },
  { key: "registrationNumber", label: "Company registration number" }, { key: "taxId", label: "Tax / VAT / GST number" },
  { key: "defaultCurrency", label: "Default currency" }, { key: "defaultLanguage", label: "Default language" },
  { key: "timezone", label: "Timezone" }, { key: "defaultCompanyCode", label: "Default company code" },
  { key: "fiscalYearVariant", label: "Fiscal year variant" }, { key: "financeContact", label: "Finance contact", type: "email" },
  { key: "website", label: "Website", type: "url" }, { key: "phone", label: "Phone" },
];

export function CompanySettingsPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["settings", "company"], queryFn: settingsApi.getCompanySettings });
  const form = useForm<CompanySettingsForm>({ resolver: zodResolver(companySettingsSchema), defaultValues: query.data });
  useEffect(() => { if (query.data) form.reset(query.data); }, [form, query.data]);
  useUnsavedChanges(form.formState.isDirty);
  const save = useMutation({ mutationFn: settingsApi.saveCompanySettings, onSuccess: (data) => { form.reset(data); toast.success("Company settings saved", "Tenant validation and posting defaults were updated."); }, onError: (error) => toast.error("Unable to save company settings", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading company settings..." />;
  if (query.isError) return <ErrorState title="Company settings unavailable" description="The tenant configuration could not be loaded." onRetry={() => query.refetch()} />;
  return <form className="space-y-6" onSubmit={form.handleSubmit((value) => save.mutate(value))}>
    <PageHeader eyebrow="Phase 12 · Administration" title="Company settings" description="Production company profile, localization, finance defaults, and tenant identity." />
    <Card><CardHeader><CardTitle>Company profile</CardTitle><CardDescription>These values are used across ingestion, validation, audit evidence, and accounting payloads.</CardDescription></CardHeader><CardContent className="grid gap-5 md:grid-cols-2">{fields.map((field) => <div key={field.key} className="space-y-2"><Label htmlFor={field.key}>{field.label}</Label><Input id={field.key} type={field.type} {...form.register(field.key)} aria-invalid={Boolean(form.formState.errors[field.key])} />{form.formState.errors[field.key]?.message ? <p className="text-xs text-red-600">{String(form.formState.errors[field.key]?.message)}</p> : null}</div>)}</CardContent></Card>
    <SettingsFormActions dirty={form.formState.isDirty} saving={save.isPending} onCancel={() => form.reset(query.data)} />
  </form>;
}
