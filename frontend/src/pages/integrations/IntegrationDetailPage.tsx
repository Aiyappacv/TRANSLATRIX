import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Database, FileDown, RefreshCw, Save, TestTube2 } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type {
  AccountMappingRow,
  CategoryMappingRow,
  ConnectorLog,
  IntegrationCapabilities,
  IntegrationConnectionField,
  IntegrationConnectionSettings,
  IntegrationDetail,
  IntegrationMappingRow,
  TaxMappingRow,
} from "@/types";
import { accountingIntegrationApi } from "@/services/accountingIntegrationApi";
import { integrationConfigSchema } from "@/schemas/integration.schema";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { IntegrationLogo } from "@/components/integrations/IntegrationLogo";
import { IntegrationStatusBadge } from "@/components/integrations/IntegrationStatusBadge";
import { MappingGrid } from "@/components/integrations/MappingGrid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

const logColumns: ColumnDef<ConnectorLog>[] = [
  { accessorKey: "timestamp", header: "Timestamp", cell: ({ row }) => formatDateTime(row.original.timestamp) },
  { accessorKey: "level", header: "Level", cell: ({ row }) => <Badge variant={row.original.level === "error" ? "danger" : row.original.level === "warning" ? "warning" : row.original.level === "success" ? "success" : "info"}>{row.original.level}</Badge> },
  { accessorKey: "operation", header: "Operation", cell: ({ row }) => <span className="font-mono text-xs">{row.original.operation}</span> },
  { accessorKey: "message", header: "Message" },
  { accessorKey: "correlationId", header: "Correlation ID", cell: ({ row }) => <span className="font-mono text-xs">{row.original.correlationId}</span> },
  { accessorKey: "durationMs", header: "Duration", cell: ({ row }) => row.original.durationMs ? `${row.original.durationMs}ms` : "—" },
];

const defaultCapabilities: IntegrationCapabilities = {
  connectionTest: true,
  fieldMapping: true,
  financialMapping: true,
  masterDataSync: true,
  workerSync: false,
  ticketSync: false,
  tallyExport: false,
};

function clone<T>(value: T): T {
  return structuredClone(value);
}

function updateConnectionField(settings: IntegrationConnectionSettings, field: IntegrationConnectionField, value: string): IntegrationConnectionSettings {
  const known = ["baseUrl", "companyCode", "tenantId", "clientId", "clientSecret", "apiKey", "webhookUrl"] as const;
  if ((known as readonly string[]).includes(field.key)) return { ...settings, [field.key]: value };
  return { ...settings, customValues: { ...settings.customValues, [field.key]: value } };
}

function readConnectionField(settings: IntegrationConnectionSettings, field: IntegrationConnectionField) {
  const value = settings[field.key as keyof IntegrationConnectionSettings];
  if (typeof value === "string") return value;
  return settings.customValues[field.key] ?? "";
}

export function IntegrationDetailPage() {
  const { providerCode = "" } = useParams();
  const toast = useToast();
  const queryClient = useQueryClient();
  const integration = useQuery({
    queryKey: ["integration-detail", providerCode],
    queryFn: () => accountingIntegrationApi.getIntegrationDetail(providerCode),
    enabled: Boolean(providerCode),
  });
  const [draft, setDraft] = useState<IntegrationDetail | null>(null);

  useEffect(() => {
    if (integration.data) setDraft(clone(integration.data));
  }, [integration.data]);

  const save = useMutation({
    mutationFn: (detail: IntegrationDetail) => {
      const parsed = integrationConfigSchema.safeParse(detail.settings);
      if (!parsed.success) throw new Error(parsed.error.issues[0]?.message ?? "Connection settings are invalid.");
      const missingField = (detail.provider.connectionFields ?? []).find((field) => field.required && !readConnectionField(detail.settings, field).trim());
      if (missingField) throw new Error(`${missingField.label} is required.`);
      return accountingIntegrationApi.saveIntegrationDetail(providerCode, detail);
    },
    onSuccess: (data) => {
      setDraft(clone(data));
      queryClient.setQueryData(["integration-detail", providerCode], data);
      queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      toast.success("Integration saved", "Connection and mapping configuration were updated.");
    },
    onError: (error) => toast.error("Unable to save integration", error instanceof Error ? error.message : "Unexpected error"),
  });

  const test = useMutation({
    mutationFn: () => accountingIntegrationApi.testProvider(providerCode),
    onSuccess: (result) => {
      integration.refetch();
      queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      if (result.status === "failed") {
        toast.error("Connection test failed", result.message);
        return;
      }
      toast.success("Connection test passed", `${result.message} Latency: ${result.latencyMs}ms.`);
    },
    onError: (error) => toast.error("Connection test failed", error instanceof Error ? error.message : "Unexpected error"),
  });

  const sync = useMutation({
    mutationFn: () => accountingIntegrationApi.syncMasterData(providerCode),
    onSuccess: (result) => {
      integration.refetch();
      queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      toast.success("Synchronization completed", result.message);
    },
    onError: (error) => toast.error("Synchronization failed", error instanceof Error ? error.message : "Unexpected error"),
  });

  if (integration.isLoading || (!draft && !integration.isError)) return <LoadingState label="Loading connector configuration..." />;
  if (integration.isError || !draft) return <ErrorState title="Integration not found" description={integration.error instanceof Error ? integration.error.message : "The requested connector is unavailable."} onRetry={() => integration.refetch()} />;

  const provider = draft.provider;
  const capabilities: IntegrationCapabilities = { ...defaultCapabilities, ...provider.capabilities };
  const updateSettings = (patch: Partial<IntegrationConnectionSettings>) => setDraft({ ...draft, settings: { ...draft.settings, ...patch } });
  const summaryMetrics = draft.summaryMetrics ?? [
    { key: "vendors", label: "Vendors", value: draft.masterData.vendors },
    { key: "customers", label: "Customers", value: draft.masterData.customers },
    { key: "accounts", label: "Accounts", value: draft.masterData.accounts },
    { key: "taxCodes", label: "Tax codes", value: draft.masterData.taxCodes },
    { key: "lastSync", label: "Last sync", value: draft.masterData.lastSyncedAt ? formatDateTime(draft.masterData.lastSyncedAt) : "Never" },
  ];
  const syncLabel = provider.syncActionLabel ?? (capabilities.workerSync ? "Sync Workday data" : "Sync master data");

  return (
    <>
      <PageHeader
        eyebrow="Integration detail"
        title={provider.name}
        description={provider.description}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline"><Link to="/app/integrations/accounting"><ArrowLeft className="h-4 w-4" />All integrations</Link></Button>
            {capabilities.tallyExport ? <Button asChild variant="outline"><Link to="/app/integrations/tally-export"><FileDown className="h-4 w-4" />Tally export</Link></Button> : null}
            {capabilities.connectionTest ? <Button variant="outline" disabled={test.isPending} onClick={() => test.mutate()}><TestTube2 className="h-4 w-4" />{test.isPending ? "Testing..." : "Test connection"}</Button> : null}
            {capabilities.masterDataSync ? <Button variant="outline" disabled={sync.isPending} onClick={() => sync.mutate()}><RefreshCw className={`h-4 w-4 ${sync.isPending ? "animate-spin" : ""}`} />{sync.isPending ? "Syncing..." : syncLabel}</Button> : null}
            <Button disabled={save.isPending} onClick={() => save.mutate(draft)}><Save className="h-4 w-4" />{save.isPending ? "Saving..." : "Save changes"}</Button>
          </div>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-[1fr_1.6fr]">
        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <IntegrationLogo provider={provider} className="h-14 w-14" />
            <div>
              <div className="flex flex-wrap items-center gap-2"><p className="text-lg font-bold">{provider.name}</p><IntegrationStatusBadge status={provider.status} /></div>
              <p className="mt-1 text-sm text-slate-500">{provider.environment ?? "Not configured"} · {provider.version ?? "Canonical adapter v1"}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="grid grid-cols-2 gap-3 p-5 md:grid-cols-5">
            {summaryMetrics.slice(0, 5).map((metric) => <div key={metric.key}><p className="text-xs text-slate-500">{metric.label}</p><p className="mt-1 text-lg font-bold">{metric.value}</p></div>)}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="connection">
        <div className="overflow-x-auto pb-1">
          <TabsList className="min-w-max">
            <TabsTrigger value="connection">Connection settings</TabsTrigger>
            {capabilities.fieldMapping ? <TabsTrigger value="fields">Field mapping</TabsTrigger> : null}
            {capabilities.financialMapping ? <TabsTrigger value="categories">Category mapping</TabsTrigger> : null}
            {capabilities.financialMapping ? <TabsTrigger value="accounts">Account mapping</TabsTrigger> : null}
            {capabilities.financialMapping ? <TabsTrigger value="tax">Tax mapping</TabsTrigger> : null}
            <TabsTrigger value="logs">Connector logs</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="connection">
          <div className="grid gap-6 xl:grid-cols-[1fr_0.72fr]">
            <Card>
              <CardHeader><CardTitle>Connection settings</CardTitle><CardDescription>Provider-specific fields are rendered from the connector registry and submitted through the shared integration backend contract.</CardDescription></CardHeader>
              <CardContent className="grid gap-5 md:grid-cols-2">
                <div className="md:col-span-2"><Label htmlFor="displayName">Connection display name</Label><Input id="displayName" className="mt-2" value={draft.settings.displayName} onChange={(event) => updateSettings({ displayName: event.target.value })} /></div>
                <div><Label>Environment</Label><Select value={draft.settings.environment} onValueChange={(value) => updateSettings({ environment: value as IntegrationConnectionSettings["environment"] })}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="sandbox">Sandbox</SelectItem><SelectItem value="development">Development</SelectItem><SelectItem value="uat">UAT</SelectItem><SelectItem value="production">Production</SelectItem><SelectItem value="local">Local bridge</SelectItem></SelectContent></Select></div>
                <div><Label>Authentication type</Label><Select value={draft.settings.authType} onValueChange={(value) => updateSettings({ authType: value as IntegrationConnectionSettings["authType"] })}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent>{(provider.authTypes ?? ["none"]).map((authType) => <SelectItem key={authType} value={authType}>{authType.replaceAll("_", " ")}</SelectItem>)}</SelectContent></Select></div>

                {(provider.connectionFields ?? []).map((field) => {
                  const value = readConnectionField(draft.settings, field);
                  return (
                    <div key={field.key} className={field.type === "textarea" ? "md:col-span-2" : ""}>
                      <Label htmlFor={field.key}>{field.label}{field.required ? " *" : ""}</Label>
                      {field.type === "select" ? (
                        <Select value={value} onValueChange={(next) => setDraft({ ...draft, settings: updateConnectionField(draft.settings, field, next) })}><SelectTrigger className="mt-2"><SelectValue placeholder={field.placeholder} /></SelectTrigger><SelectContent>{(field.options ?? []).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select>
                      ) : field.type === "textarea" ? (
                        <Textarea id={field.key} className="mt-2" value={value} placeholder={field.placeholder} onChange={(event) => setDraft({ ...draft, settings: updateConnectionField(draft.settings, field, event.target.value) })} />
                      ) : (
                        <Input id={field.key} className="mt-2" type={field.type === "password" ? "password" : field.type === "number" ? "number" : field.type === "url" ? "url" : "text"} value={value} placeholder={field.placeholder} onChange={(event) => setDraft({ ...draft, settings: updateConnectionField(draft.settings, field, event.target.value) })} />
                      )}
                      {field.helpText ? <p className="mt-1 text-xs text-slate-500">{field.helpText}</p> : null}
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader><CardTitle>Connector behavior</CardTitle><CardDescription>Control connector availability and provider-supported synchronization.</CardDescription></CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><div><p className="text-sm font-semibold">Enable connector</p><p className="mt-1 text-xs text-slate-500">Allow this provider to be used by company workflows.</p></div><Switch checked={draft.settings.enabled} onCheckedChange={(checked) => updateSettings({ enabled: checked })} /></div>
                  {capabilities.masterDataSync ? <><div className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><div><p className="text-sm font-semibold">Automatic synchronization</p><p className="mt-1 text-xs text-slate-500">Run the provider-specific data synchronization on a schedule.</p></div><Switch checked={draft.settings.autoSyncEnabled} onCheckedChange={(checked) => updateSettings({ autoSyncEnabled: checked })} /></div><div><Label>Sync frequency</Label><Select value={draft.settings.syncFrequency} onValueChange={(value) => updateSettings({ syncFrequency: value as IntegrationConnectionSettings["syncFrequency"] })}><SelectTrigger className="mt-2"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="manual">Manual</SelectItem><SelectItem value="hourly">Hourly</SelectItem><SelectItem value="daily">Daily</SelectItem><SelectItem value="weekly">Weekly</SelectItem></SelectContent></Select></div></> : null}
                </CardContent>
              </Card>
              <Card><CardHeader><CardTitle>Supported actions</CardTitle><CardDescription>Capabilities declared by the provider adapter.</CardDescription></CardHeader><CardContent className="space-y-2">{(provider.supportedActions ?? []).map((action) => <div key={action} className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"><CheckCircle2 className="h-4 w-4" />{action}</div>)}</CardContent></Card>
            </div>
          </div>
        </TabsContent>

        {capabilities.fieldMapping ? <TabsContent value="fields"><Card><CardHeader><CardTitle>Field mapping</CardTitle><CardDescription>Map canonical TRANSLATRIX fields to provider-specific payload fields and transformations.</CardDescription></CardHeader><CardContent><MappingGrid<IntegrationMappingRow> rows={draft.fieldMappings} columns={[{ key: "sourceField", label: "Source field" }, { key: "targetField", label: "Target field" }, { key: "transform", label: "Transform" }, { key: "defaultValue", label: "Default value" }, { key: "required", label: "Required", type: "boolean" }, { key: "active", label: "Active", type: "boolean" }]} onChange={(fieldMappings) => setDraft({ ...draft, fieldMappings })} onAdd={() => ({ id: crypto.randomUUID(), sourceField: "", targetField: "", transform: "", defaultValue: "", required: false, active: true })} /></CardContent></Card></TabsContent> : null}
        {capabilities.financialMapping ? <TabsContent value="categories"><Card><CardHeader><CardTitle>Category mapping</CardTitle><CardDescription>Translate finance categories and subcategories into provider transaction types.</CardDescription></CardHeader><CardContent><MappingGrid<CategoryMappingRow> rows={draft.categoryMappings} columns={[{ key: "sourceCategory", label: "Source category" }, { key: "sourceSubcategory", label: "Source subcategory" }, { key: "targetType", label: "Target type" }, { key: "targetValue", label: "Target value" }, { key: "active", label: "Active", type: "boolean" }]} onChange={(categoryMappings) => setDraft({ ...draft, categoryMappings })} onAdd={() => ({ id: crypto.randomUUID(), sourceCategory: "", sourceSubcategory: "", targetType: "", targetValue: "", active: true })} /></CardContent></Card></TabsContent> : null}
        {capabilities.financialMapping ? <TabsContent value="accounts"><Card><CardHeader><CardTitle>Account mapping</CardTitle><CardDescription>Map tenant GL accounts to the provider chart of accounts by company code.</CardDescription></CardHeader><CardContent><MappingGrid<AccountMappingRow> rows={draft.accountMappings} columns={[{ key: "sourceAccount", label: "Source account" }, { key: "sourceLabel", label: "Source label" }, { key: "targetAccount", label: "Target account" }, { key: "targetLabel", label: "Target label" }, { key: "companyCode", label: "Company code" }, { key: "active", label: "Active", type: "boolean" }]} onChange={(accountMappings) => setDraft({ ...draft, accountMappings })} onAdd={() => ({ id: crypto.randomUUID(), sourceAccount: "", sourceLabel: "", targetAccount: "", targetLabel: "", companyCode: "", active: true })} /></CardContent></Card></TabsContent> : null}
        {capabilities.financialMapping ? <TabsContent value="tax"><Card><CardHeader><CardTitle>Tax mapping</CardTitle><CardDescription>Map source tax codes and rates to provider-specific codes and jurisdictions.</CardDescription></CardHeader><CardContent><MappingGrid<TaxMappingRow> rows={draft.taxMappings} columns={[{ key: "sourceTaxCode", label: "Source tax code" }, { key: "sourceRate", label: "Source rate %", type: "number" }, { key: "targetTaxCode", label: "Target tax code" }, { key: "targetRate", label: "Target rate %", type: "number" }, { key: "jurisdiction", label: "Jurisdiction" }, { key: "active", label: "Active", type: "boolean" }]} onChange={(taxMappings) => setDraft({ ...draft, taxMappings })} onAdd={() => ({ id: crypto.randomUUID(), sourceTaxCode: "", sourceRate: 0, targetTaxCode: "", targetRate: 0, jurisdiction: "", active: true })} /></CardContent></Card></TabsContent> : null}
        <TabsContent value="logs"><Card><CardHeader><div className="flex items-center justify-between gap-4"><div><CardTitle>Connector logs</CardTitle><CardDescription>Connection tests, API calls, synchronization runs, latency, and correlation IDs.</CardDescription></div><Button variant="outline" onClick={() => integration.refetch()}><RefreshCw className="h-4 w-4" />Refresh logs</Button></div></CardHeader><CardContent><DataTable columns={logColumns} data={draft.logs} searchPlaceholder="Search operation, message, or correlation ID..." exportFileName={`${provider.code}-connector-logs`} dense /></CardContent></Card></TabsContent>
      </Tabs>

      <div className="mt-6 rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-900 dark:border-indigo-900/60 dark:bg-indigo-950/30 dark:text-indigo-200"><div className="flex items-start gap-3"><Database className="mt-0.5 h-5 w-5" /><div><p className="font-semibold">Backend integration contract</p><p className="mt-1">Provider metadata declares authentication, connection fields, supported actions, capabilities, mappings, synchronization, and logs. Workday and ServiceNow use the same tenant-aware API client while displaying only relevant configuration sections.</p></div></div></div>
    </>
  );
}
