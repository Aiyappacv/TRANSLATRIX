import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Clock3, Plus, RefreshCw, Search, Settings2, TestTube2 } from "lucide-react";
import type { CustomConnectorInput, IntegrationAuthType, IntegrationEnvironment, IntegrationProviderType, IntegrationStatus } from "@/types";
import { accountingIntegrationApi } from "@/services/accountingIntegrationApi";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { IntegrationLogo } from "@/components/integrations/IntegrationLogo";
import { IntegrationStatusBadge } from "@/components/integrations/IntegrationStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

const initialConnector: CustomConnectorInput = {
  name: "",
  code: "",
  type: "api",
  description: "",
  baseUrl: "",
  authType: "api_key",
  environment: "sandbox",
};

export function AccountingIntegrationsPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const [connectorOpen, setConnectorOpen] = useState(false);
  const [connector, setConnector] = useState<CustomConnectorInput>(initialConnector);
  const requestedType = searchParams.get("type");
  const supportedTypes: IntegrationProviderType[] = ["erp", "accounting", "export", "api", "hris", "itsm", "storage", "ocr", "translation"];
  const typeFilter: "all" | IntegrationProviderType = requestedType && supportedTypes.includes(requestedType as IntegrationProviderType)
    ? requestedType as IntegrationProviderType
    : "all";
  const setTypeFilter = (value: "all" | IntegrationProviderType) => {
    const next = new URLSearchParams(searchParams);
    if (value === "all") next.delete("type");
    else next.set("type", value);
    setSearchParams(next, { replace: true });
  };
  const [statusFilter, setStatusFilter] = useState<"all" | IntegrationStatus>("all");
  const providers = useQuery({ queryKey: ["integration-providers"], queryFn: accountingIntegrationApi.getProviders });
  const test = useMutation({
    mutationFn: accountingIntegrationApi.testProvider,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      if (result.status === "failed") {
        toast.error("Connection test failed", result.message);
        return;
      }
      toast.success("Connection test passed", `${result.providerCode} responded in ${result.latencyMs}ms.`);
    },
    onError: (error) => toast.error("Connection test failed", error instanceof Error ? error.message : "Unexpected connector error."),
  });
  const registerConnector = useMutation({
    mutationFn: accountingIntegrationApi.registerCustomConnector,
    onSuccess: async (detail) => {
      await queryClient.invalidateQueries({ queryKey: ["integration-providers"] });
      setConnectorOpen(false);
      setConnector(initialConnector);
      toast.success("Custom connector registered", `${detail.provider.name} is ready for connection settings and field mapping.`);
      navigate(`/app/integrations/${detail.provider.code}`);
    },
    onError: (error) => toast.error("Connector registration failed", error instanceof Error ? error.message : "Unable to register connector."),
  });

  const submitConnector = () => {
    if (!connector.name.trim() || !connector.code.trim() || !connector.description.trim()) {
      toast.error("Complete the connector profile", "Name, code, and description are required.");
      return;
    }
    if (!/^https?:\/\//i.test(connector.baseUrl)) {
      toast.error("Enter a valid base URL", "The connector base URL must begin with http:// or https://.");
      return;
    }
    registerConnector.mutate(connector);
  };

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (providers.data ?? []).filter((provider) => {
      const matchesSearch = !term || [provider.name, provider.description, ...(provider.supportedActions ?? [])].join(" ").toLowerCase().includes(term);
      const matchesType = typeFilter === "all" || provider.type === typeFilter;
      const matchesStatus = statusFilter === "all" || provider.status === statusFilter;
      return matchesSearch && matchesType && matchesStatus;
    });
  }, [providers.data, search, typeFilter, statusFilter]);

  if (providers.isLoading) return <LoadingState label="Loading accounting integrations..." />;
  if (providers.isError) return <ErrorState title="Integration catalog unavailable" description={providers.error instanceof Error ? providers.error.message : "Unable to load connector providers."} onRetry={() => providers.refetch()} />;

  const connectedCount = (providers.data ?? []).filter((provider) => provider.status === "connected").length;
  const attentionCount = (providers.data ?? []).filter((provider) => provider.status === "degraded" || provider.status === "error").length;

  return (
    <>
      <PageHeader
        eyebrow="Phase 9 · Integrations"
        title="Enterprise integrations"
        description="Configure ERP, accounting, Tally export, Workday, ServiceNow, and extensible API connectors through one backend contract."
        actions={<Button onClick={() => setConnectorOpen(true)}><Plus className="h-4 w-4" />Register custom connector</Button>}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Connector catalog</p><p className="mt-2 text-3xl font-bold">{providers.data?.length ?? 0}</p><p className="mt-2 text-xs text-slate-500">ERP, accounting, export, HRIS, ITSM, and API adapters</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Connected</p><p className="mt-2 text-3xl font-bold text-emerald-600">{connectedCount}</p><p className="mt-2 text-xs text-slate-500">Ready for posting or export</p></CardContent></Card>
        <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Needs attention</p><p className="mt-2 text-3xl font-bold text-amber-600">{attentionCount}</p><p className="mt-2 text-xs text-slate-500">Degraded or failed health checks</p></CardContent></Card>
      </div>

      <Card className="mb-6">
        <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_220px_220px_auto]">
          <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><Input className="pl-9" placeholder="Search integrations and supported actions..." value={search} onChange={(event) => setSearch(event.target.value)} /></div>
          <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as "all" | IntegrationProviderType)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All connector types</SelectItem><SelectItem value="erp">ERP</SelectItem><SelectItem value="accounting">Accounting</SelectItem><SelectItem value="export">Export</SelectItem><SelectItem value="api">API / Webhook</SelectItem><SelectItem value="hris">HRIS</SelectItem><SelectItem value="itsm">ITSM</SelectItem></SelectContent></Select>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as "all" | IntegrationStatus)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All statuses</SelectItem><SelectItem value="connected">Connected</SelectItem><SelectItem value="available">Available</SelectItem><SelectItem value="degraded">Degraded</SelectItem><SelectItem value="disabled">Disabled</SelectItem><SelectItem value="error">Error</SelectItem></SelectContent></Select>
          <Button variant="outline" onClick={() => providers.refetch()}><RefreshCw className={`h-4 w-4 ${providers.isFetching ? "animate-spin" : ""}`} />Refresh</Button>
        </CardContent>
      </Card>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((provider) => {
          const isTesting = test.isPending && test.variables === provider.code;
          const configurePath = provider.code === "sap_s4hana" ? "/app/integrations/sap/settings" : `/app/integrations/${provider.code}`;
          return (
            <Card key={provider.code} className="flex h-full flex-col overflow-hidden">
              <CardHeader className="space-y-4">
                <div className="flex items-start justify-between gap-4"><IntegrationLogo provider={provider} /><IntegrationStatusBadge status={provider.status} /></div>
                <div><div className="flex flex-wrap items-center gap-2"><CardTitle>{provider.name}</CardTitle><Badge variant="neutral">{provider.type}</Badge></div><CardDescription className="mt-2 min-h-10">{provider.description}</CardDescription></div>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col gap-5">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-slate-500">Environment</p><p className="mt-1 font-semibold capitalize text-slate-900 dark:text-slate-100">{provider.environment ?? "Not configured"}</p></div>
                  <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-slate-500">Last sync</p><p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{provider.lastSyncAt ? formatDateTime(provider.lastSyncAt) : "Never"}</p></div>
                </div>
                <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Supported actions</p><div className="flex flex-wrap gap-2">{(provider.supportedActions ?? []).slice(0, 4).map((action) => <Badge key={action} variant="info">{action}</Badge>)}</div></div>
                <div className="mt-auto space-y-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                  <Button asChild className="w-full"><Link to={configurePath}><Settings2 className="h-4 w-4" />Configure<ArrowRight className="ml-auto h-4 w-4" /></Link></Button>
                  <div className="grid grid-cols-2 gap-2">
                    <Button asChild variant="outline" size="sm"><Link to={`/app/integrations/${provider.code}`}><Clock3 className="h-4 w-4" />Details & logs</Link></Button>
                    <Button variant="outline" size="sm" disabled={isTesting} onClick={() => test.mutate(provider.code)}>{provider.status === "connected" ? <CheckCircle2 className="h-4 w-4" /> : <TestTube2 className="h-4 w-4" />}{isTesting ? "Testing..." : "Test"}</Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {!filtered.length ? <Card><CardContent className="flex min-h-52 items-center justify-center text-sm text-slate-500">No integrations match the current filters.</CardContent></Card> : null}

      <Dialog open={connectorOpen} onOpenChange={setConnectorOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Register custom connector</DialogTitle><DialogDescription>Create a typed connector contract now, then configure credentials, mappings, tests, and logs on its detail page.</DialogDescription></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2"><Label htmlFor="connector-name">Connector name</Label><Input id="connector-name" value={connector.name} onChange={(event) => setConnector((value) => ({ ...value, name: event.target.value, code: value.code || event.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_") }))} placeholder="Example ERP Gateway" /></div>
            <div className="space-y-2"><Label htmlFor="connector-code">Unique code</Label><Input id="connector-code" value={connector.code} onChange={(event) => setConnector((value) => ({ ...value, code: event.target.value }))} placeholder="example_erp_gateway" /></div>
            <div className="space-y-2"><Label>Connector type</Label><Select value={connector.type} onValueChange={(value) => setConnector((current) => ({ ...current, type: value as IntegrationProviderType }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{supportedTypes.map((type) => <SelectItem key={type} value={type}>{type.toUpperCase()}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Environment</Label><Select value={connector.environment} onValueChange={(value) => setConnector((current) => ({ ...current, environment: value as IntegrationEnvironment }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["sandbox", "development", "uat", "production", "local"].map((environment) => <SelectItem key={environment} value={environment}>{environment}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Authentication</Label><Select value={connector.authType} onValueChange={(value) => setConnector((current) => ({ ...current, authType: value as IntegrationAuthType }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["oauth2", "client_credentials", "api_key", "basic", "certificate", "sftp_key", "none"].map((authType) => <SelectItem key={authType} value={authType}>{authType.replaceAll("_", " ")}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label htmlFor="connector-url">Base URL</Label><Input id="connector-url" type="url" value={connector.baseUrl} onChange={(event) => setConnector((value) => ({ ...value, baseUrl: event.target.value }))} placeholder="Connector base URL" /></div>
            <div className="space-y-2 md:col-span-2"><Label htmlFor="connector-description">Description</Label><Textarea id="connector-description" className="min-h-24" value={connector.description} onChange={(event) => setConnector((value) => ({ ...value, description: event.target.value }))} placeholder="Describe the finance or operational workflow supported by this connector." /></div>
          </div>
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setConnectorOpen(false)}>Cancel</Button><Button disabled={registerConnector.isPending} onClick={submitConnector}>{registerConnector.isPending ? "Registering..." : "Register connector"}</Button></div>
        </DialogContent>
      </Dialog>
    </>
  );
}
