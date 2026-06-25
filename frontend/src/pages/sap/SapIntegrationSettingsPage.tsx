import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable, CheckCircle2, Clock3, KeyRound, Save, ShieldCheck, TestTube2 } from "lucide-react";
import { sapApi } from "@/services/sapApi";
import { sapConnectionSchema, type SapConnectionForm } from "@/schemas/sap.schema";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

const apiOptions = [
  { value: "journal_entry", label: "Journal Entry API" },
  { value: "supplier_invoice", label: "Supplier Invoice API" },
  { value: "customer_invoice", label: "Customer Invoice API" },
  { value: "asset_accounting", label: "Asset Accounting API" },
  { value: "bank_statement", label: "Bank Statement API" },
] as const;

function FieldError({ message }: { message?: string }) {
  return message ? <p className="mt-1 text-xs text-red-600">{message}</p> : null;
}

export function SapIntegrationSettingsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["sap-settings"], queryFn: sapApi.getSettings });
  const form = useForm<SapConnectionForm>({
    resolver: zodResolver(sapConnectionSchema),
    defaultValues: {
      systemName: "",
      environment: "sandbox",
      baseUrl: "",
      authType: "oauth2_client_credentials",
      clientId: "",
      clientSecret: "",
      companyCode: "",
      apiSelection: ["journal_entry"],
      requestTimeoutSeconds: 45,
      retryLimit: 3,
      idempotencyEnabled: true,
      certificateValidationEnabled: true,
    },
  });

  useEffect(() => {
    if (!settings.data) return;
    form.reset({
      systemName: settings.data.systemName,
      environment: settings.data.environment,
      baseUrl: settings.data.baseUrl,
      authType: settings.data.authType,
      clientId: settings.data.clientId,
      clientSecret: "",
      companyCode: settings.data.companyCode,
      apiSelection: settings.data.apiSelection,
      requestTimeoutSeconds: settings.data.requestTimeoutSeconds,
      retryLimit: settings.data.retryLimit,
      idempotencyEnabled: settings.data.idempotencyEnabled,
      certificateValidationEnabled: settings.data.certificateValidationEnabled,
    });
  }, [settings.data, form]);

  const save = useMutation({
    mutationFn: (values: SapConnectionForm) => {
      if (!settings.data) throw new Error("SAP settings are not loaded.");
      return sapApi.saveSettings({ ...settings.data, ...values, clientSecret: values.clientSecret || settings.data.clientSecret });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["sap-settings"], data);
      toast.success("SAP settings saved", "Connection settings and API selections were updated.");
    },
    onError: (error) => toast.error("Unable to save SAP settings", error instanceof Error ? error.message : "Unexpected error"),
  });

  const test = useMutation({
    mutationFn: () => sapApi.testConnection(form.getValues()),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["sap-settings"] });
      queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      if (result.status === "failed") {
        toast.error("SAP connection failed", result.message);
        return;
      }
      toast.success("SAP connection passed", `${result.systemVersion ?? "SAP system"} responded in ${result.latencyMs}ms.`);
    },
    onError: (error) => toast.error("SAP connection failed", error instanceof Error ? error.message : "Unexpected error"),
  });

  if (settings.isLoading) return <LoadingState label="Loading SAP integration settings..." />;
  if (settings.isError || !settings.data) return <ErrorState title="SAP settings unavailable" description={settings.error instanceof Error ? settings.error.message : "Unable to load the current SAP configuration."} onRetry={() => settings.refetch()} />;

  const current = settings.data;

  return (
    <>
      <PageHeader
        eyebrow="Integrations · SAP S/4HANA"
        title="SAP integration settings"
        description="Configure the SAP system endpoint, authentication, company code, selected APIs, and production posting safeguards."
        actions={<Button variant="outline" disabled={test.isPending} onClick={() => test.mutate()}><TestTube2 className={`h-4 w-4 ${test.isPending ? "animate-pulse" : ""}`} />Test connection</Button>}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card><CardContent className="flex items-center gap-3 p-5"><div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"><Cable className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Connection</p><div className="mt-1"><Badge variant={current.status === "connected" ? "success" : current.status === "degraded" ? "warning" : "neutral"}>{current.status.replaceAll("_", " ")}</Badge></div></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3 p-5"><div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-700 dark:bg-indigo-950/30 dark:text-indigo-300"><Clock3 className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Last tested</p><p className="mt-1 text-sm font-semibold">{current.lastTestedAt ? formatDateTime(current.lastTestedAt) : "Never"}{current.lastTestLatencyMs ? ` · ${current.lastTestLatencyMs}ms` : ""}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3 p-5"><div className="rounded-xl bg-blue-50 p-2.5 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300"><ShieldCheck className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Posting guardrails</p><p className="mt-1 text-sm font-semibold">Idempotency + TLS validation</p></div></CardContent></Card>
      </div>

      <form onSubmit={form.handleSubmit((values) => save.mutate(values))} className="grid gap-6 xl:grid-cols-[1fr_0.78fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>System and endpoint</CardTitle><CardDescription>Use environment-specific credentials and API hosts. Secrets are never displayed after storage.</CardDescription></CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2">
              <div className="md:col-span-2"><Label htmlFor="systemName">SAP system name</Label><Input id="systemName" className="mt-2" {...form.register("systemName")} /><FieldError message={form.formState.errors.systemName?.message} /></div>
              <div><Label>Environment</Label><Controller control={form.control} name="environment" render={({ field }) => <Select value={field.value} onValueChange={field.onChange}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="sandbox">Sandbox</SelectItem><SelectItem value="development">Development</SelectItem><SelectItem value="quality">Quality</SelectItem><SelectItem value="uat">UAT</SelectItem><SelectItem value="production">Production</SelectItem></SelectContent></Select>} /></div>
              <div><Label htmlFor="companyCode">Company code</Label><Input id="companyCode" className="mt-2 font-mono" {...form.register("companyCode")} /><FieldError message={form.formState.errors.companyCode?.message} /></div>
              <div className="md:col-span-2"><Label htmlFor="baseUrl">Base URL</Label><Input id="baseUrl" className="mt-2 font-mono text-xs" {...form.register("baseUrl")} /><FieldError message={form.formState.errors.baseUrl?.message} /></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Authentication</CardTitle><CardDescription>Credential values should be stored by the backend in a secrets manager.</CardDescription></CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2">
              <div><Label>Auth type</Label><Controller control={form.control} name="authType" render={({ field }) => <Select value={field.value} onValueChange={field.onChange}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="oauth2_client_credentials">OAuth 2.0 client credentials</SelectItem><SelectItem value="basic">Basic authentication</SelectItem><SelectItem value="certificate">Client certificate</SelectItem><SelectItem value="destination_service">SAP destination service</SelectItem></SelectContent></Select>} /></div>
              <div><Label htmlFor="clientId">Client ID / username</Label><Input id="clientId" className="mt-2" {...form.register("clientId")} /><FieldError message={form.formState.errors.clientId?.message} /></div>
              <div className="md:col-span-2"><Label htmlFor="clientSecret">Secret placeholder</Label><div className="relative mt-2"><KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><Input id="clientSecret" type="password" className="pl-9" placeholder="Leave blank to keep the stored secret" {...form.register("clientSecret")} /></div><p className="mt-1 text-xs text-slate-500">The existing secret is retained unless a new value is entered.</p></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>API selection</CardTitle><CardDescription>Select only APIs enabled in the target SAP system and required by approved mappings.</CardDescription></CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">{apiOptions.map((option) => <label key={option.value} className="flex items-center gap-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><Checkbox value={option.value} {...form.register("apiSelection")} /><span className="text-sm font-medium">{option.label}</span></label>)}</div>
              <FieldError message={form.formState.errors.apiSelection?.message} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Reliability controls</CardTitle><CardDescription>Safe defaults for production posting and transient failures.</CardDescription></CardHeader>
            <CardContent className="space-y-5">
              <div><Label htmlFor="requestTimeoutSeconds">Request timeout (seconds)</Label><Input id="requestTimeoutSeconds" type="number" className="mt-2" {...form.register("requestTimeoutSeconds")} /><FieldError message={form.formState.errors.requestTimeoutSeconds?.message} /></div>
              <div><Label htmlFor="retryLimit">Retry limit</Label><Input id="retryLimit" type="number" className="mt-2" {...form.register("retryLimit")} /><FieldError message={form.formState.errors.retryLimit?.message} /></div>
              <Controller control={form.control} name="idempotencyEnabled" render={({ field }) => <div className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><div><p className="text-sm font-semibold">Idempotency protection</p><p className="mt-1 text-xs text-slate-500">Prevent duplicate SAP documents during retries.</p></div><Switch checked={field.value} onChange={(event) => field.onChange(event.target.checked)} /></div>} />
              <Controller control={form.control} name="certificateValidationEnabled" render={({ field }) => <div className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><div><p className="text-sm font-semibold">TLS certificate validation</p><p className="mt-1 text-xs text-slate-500">Reject untrusted or expired endpoint certificates.</p></div><Switch checked={field.value} onChange={(event) => field.onChange(event.target.checked)} /></div>} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Connection validation</CardTitle><CardDescription>The test verifies authentication, company code access, and selected API availability without posting data.</CardDescription></CardHeader>
            <CardContent className="space-y-3">
              {["Resolve endpoint and validate TLS", "Authenticate with configured credentials", "Verify company code authorization", "Probe selected APIs with read-only requests"].map((item) => <div key={item} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{item}</div>)}
              <Button type="button" variant="outline" className="mt-3 w-full" disabled={test.isPending} onClick={() => test.mutate()}><TestTube2 className="h-4 w-4" />{test.isPending ? "Testing connection..." : "Test connection"}</Button>
            </CardContent>
          </Card>

          <Button type="submit" className="w-full" disabled={save.isPending || !form.formState.isDirty}><Save className="h-4 w-4" />{save.isPending ? "Saving..." : "Save SAP settings"}</Button>
        </div>
      </form>
    </>
  );
}
