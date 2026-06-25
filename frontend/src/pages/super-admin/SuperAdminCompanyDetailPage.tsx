import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2, Database, ShieldCheck, UsersRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { LoadingState } from "@/components/common/LoadingState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { formatDate, formatDateTime, formatNumber, formatPercent } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";

const tabs = ["overview", "users", "usage", "integrations", "billing", "batches", "sap-postings", "audit-logs", "security", "settings"];

export function SuperAdminCompanyDetailPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { companyId = "" } = useParams();
  const company = useQuery({ queryKey: ["super-admin", "company", companyId], queryFn: () => superAdminApi.getCompany(companyId) });
  const security = useQuery({ queryKey: ["super-admin", "company", companyId, "security"], queryFn: () => superAdminApi.getCompanySecurity(companyId), enabled: Boolean(companyId) });
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaRequiredForPrivilegedRoles, setMfaRequiredForPrivilegedRoles] = useState(false);
  useEffect(() => {
    if (security.data) {
      setMfaRequired(security.data.mfaRequired);
      setMfaRequiredForPrivilegedRoles(security.data.mfaRequiredForPrivilegedRoles);
    }
  }, [security.data]);
  const saveSecurity = useMutation({
    mutationFn: () => superAdminApi.saveCompanySecurity(companyId, {
      mfaRequired,
      mfaRequiredForPrivilegedRoles,
      resetMfaEnrollments: !mfaRequired && !mfaRequiredForPrivilegedRoles,
    }),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["super-admin", "company", companyId, "security"], updated);
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] });
      toast.success("Tenant MFA policy saved", updated.mfaRequired || updated.mfaRequiredForPrivilegedRoles ? "Users will be prompted to enroll on their next sign-in." : "MFA is disabled and existing tenant enrollments were cleared.");
    },
    onError: (error) => toast.error("Unable to save tenant MFA policy", error instanceof Error ? error.message : "Unexpected error"),
  });
  const lifecycle = useMutation({
    mutationFn: (status: "active" | "suspended") => superAdminApi.setCompanyStatus(companyId, status),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["super-admin", "company", companyId], updated);
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "companies"] });
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "dashboard"] });
      toast.success(updated.status === "active" ? "Tenant reactivated" : "Tenant suspended", `${updated.companyName} lifecycle status was updated and audited.`);
    },
    onError: (error) => toast.error("Tenant status update failed", error instanceof Error ? error.message : "Unable to update tenant status."),
  });
  if (company.isLoading) return <LoadingState label="Loading tenant..." />;
  if (!company.data) return null;
  const item = company.data;

  return (
    <>
      <PageHeader eyebrow="Audited tenant view" title={item.companyName} description={`${item.tenantId} · ${item.industry} · ${item.country}`} badge={item.plan} actions={<><Button asChild variant="outline"><Link to="/super-admin/companies"><ArrowLeft className="h-4 w-4" />Companies</Link></Button><ConfirmDialog
          destructive={item.status !== "suspended"}
          title={item.status === "suspended" ? "Reactivate tenant?" : "Suspend tenant?"}
          description={item.status === "suspended" ? "User access and processing can resume immediately. The action will be recorded in the platform audit log." : "Tenant users will lose access and processing will stop until the tenant is reactivated. The action is fully audited."}
          confirmLabel={item.status === "suspended" ? "Reactivate tenant" : "Suspend tenant"}
          onConfirm={async () => { await lifecycle.mutateAsync(item.status === "suspended" ? "active" : "suspended"); }}
          trigger={<Button disabled={lifecycle.isPending} variant={item.status === "suspended" ? "success" : "destructive"}>{lifecycle.isPending ? "Updating..." : item.status === "suspended" ? "Reactivate tenant" : "Suspend tenant"}</Button>}
        /></>} />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Users" value={formatNumber(item.users)} icon={UsersRound} />
        <MetricCard label="Files processed" value={formatNumber(item.filesProcessed)} icon={Building2} />
        <MetricCard label="Entries processed" value={formatNumber(item.entriesProcessed)} icon={Database} />
        <MetricCard label="MFA coverage" value={formatPercent(item.mfaCoverage)} tone={item.mfaCoverage >= 0.9 ? "success" : "warning"} icon={ShieldCheck} />
      </div>
      <Tabs defaultValue="overview">
        <TabsList className="h-auto w-full justify-start overflow-x-auto p-1">{tabs.map((tab) => <TabsTrigger key={tab} value={tab} className="capitalize">{tab.replaceAll("-", " ")}</TabsTrigger>)}</TabsList>
        <TabsContent value="overview">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card><CardHeader><CardTitle>Tenant profile</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{[
              ["Tenant ID", item.tenantId], ["Company admin", item.adminEmail], ["Plan", item.plan], ["Status", <PlatformStatusBadge key="status" status={item.status} />], ["Created", formatDate(item.createdAt)], ["Last activity", formatDateTime(item.lastActivityAt)], ["Billing", <PlatformStatusBadge key="billing" status={item.billingStatus} />], ["IP restrictions", item.ipRestrictionsEnabled ? "Enabled" : "Not enabled"],
            ].map(([label, value]) => <div key={String(label)} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">{label}</p><div className="mt-1 text-sm font-semibold">{value}</div></div>)}</CardContent></Card>
            <Card><CardHeader><CardTitle>Processing footprint</CardTitle><CardDescription>Lifetime tenant activity across finance workflows.</CardDescription></CardHeader><CardContent className="space-y-3">{[
              ["Files processed", item.filesProcessed], ["Entries processed", item.entriesProcessed], ["SAP postings", item.sapPostings], ["Other accounting postings", item.accountingPostings], ["Storage used", `${item.storageUsedGb} GB`],
            ].map(([label, value]) => <div key={String(label)} className="flex items-center justify-between border-b border-slate-100 py-2 text-sm last:border-0 dark:border-slate-800"><span className="text-slate-500">{label}</span><span className="font-semibold tabular">{typeof value === "number" ? formatNumber(value) : value}</span></div>)}</CardContent></Card>
          </div>
        </TabsContent>
        <TabsContent value="users"><Card><CardHeader><CardTitle>Tenant users</CardTitle><CardDescription>User directory, role assignments, MFA state, and account lifecycle are scoped to {item.companyName}.</CardDescription></CardHeader><CardContent><div className="rounded-xl border border-dashed p-8 text-center text-sm text-slate-500">{item.users} users are registered. Open the tenant workspace only when support access is approved and an audit reason is recorded.</div></CardContent></Card></TabsContent>
        <TabsContent value="usage"><Card><CardHeader><CardTitle>Tenant usage</CardTitle></CardHeader><CardContent className="grid gap-4 md:grid-cols-3"><MetricCard label="Files" value={formatNumber(item.filesProcessed)} /><MetricCard label="Entries" value={formatNumber(item.entriesProcessed)} /><MetricCard label="Storage" value={`${item.storageUsedGb} GB`} /></CardContent></Card></TabsContent>
        <TabsContent value="integrations"><Card><CardHeader><CardTitle>Connected integrations</CardTitle></CardHeader><CardContent className="flex flex-wrap gap-2"><Badge variant="success">Primary accounting connected</Badge>{item.sapPostings > 0 ? <Badge variant="brand">SAP S/4HANA active</Badge> : <Badge variant="neutral">No SAP posting</Badge>}<Badge variant="info">OCR provider configured</Badge></CardContent></Card></TabsContent>
        <TabsContent value="billing"><Card><CardHeader><CardTitle>Billing and subscription</CardTitle></CardHeader><CardContent className="space-y-3"><p className="text-sm">Plan: <strong>{item.plan}</strong></p><p className="text-sm">Billing status: <PlatformStatusBadge status={item.billingStatus} /></p>{item.trialEndsAt ? <p className="text-sm">Trial ends {formatDate(item.trialEndsAt)}</p> : null}</CardContent></Card></TabsContent>
        <TabsContent value="batches"><Card><CardHeader><CardTitle>Processing batches</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-500">Cross-tenant batch access is read-only and audited from the platform workspace.</p></CardContent></Card></TabsContent>
        <TabsContent value="sap-postings"><Card><CardHeader><CardTitle>SAP postings</CardTitle></CardHeader><CardContent><p className="text-2xl font-bold tabular">{formatNumber(item.sapPostings)}</p><p className="mt-1 text-sm text-slate-500">Lifetime SAP posting attempts for this tenant.</p></CardContent></Card></TabsContent>
        <TabsContent value="audit-logs"><Card><CardHeader><CardTitle>Tenant audit logs</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-500">Tenant activity is immutable. Platform access is recorded separately and correlated with support or operational reasons.</p></CardContent></Card></TabsContent>
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Tenant authentication policy</CardTitle>
              <CardDescription>MFA is optional by default. Enable it only when this tenant is ready to enroll users.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {security.isLoading ? <LoadingState label="Loading tenant security policy..." /> : null}
              {security.isError ? <p className="text-sm text-red-600">The tenant security policy could not be loaded.</p> : null}
              {!security.isLoading && !security.isError ? (
                <>
                  <Switch
                    label="Require MFA for every tenant user"
                    checked={mfaRequired}
                    onCheckedChange={(checked) => { setMfaRequired(checked); if (checked) setMfaRequiredForPrivilegedRoles(false); }}
                  />
                  <Switch
                    label="Require MFA only for privileged roles"
                    checked={mfaRequiredForPrivilegedRoles}
                    disabled={mfaRequired}
                    onCheckedChange={setMfaRequiredForPrivilegedRoles}
                  />
                  <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                    When both options are off, Company Admin and tenant users sign in with email and password only. Enabling MFA starts a clear enrollment flow on the next sign-in.
                  </div>
                  <div className="flex justify-end">
                    <Button onClick={() => saveSecurity.mutate()} disabled={saveSecurity.isPending}>
                      {saveSecurity.isPending ? "Saving..." : "Save MFA policy"}
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border p-3"><p className="text-xs text-slate-500">MFA coverage</p><p className="mt-1 font-semibold">{formatPercent(item.mfaCoverage)}</p></div>
                    <div className="rounded-xl border p-3"><p className="text-xs text-slate-500">IP restrictions</p><p className="mt-1 font-semibold">{item.ipRestrictionsEnabled ? "Enabled" : "Disabled"}</p></div>
                    <div className="rounded-xl border p-3"><p className="text-xs text-slate-500">Tenant isolation</p><p className="mt-1 font-semibold">Enforced</p></div>
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="settings"><Card><CardHeader><CardTitle>Tenant platform settings</CardTitle></CardHeader><CardContent><p className="text-sm text-slate-500">Only platform-scoped lifecycle, plan, retention, and support-access settings are editable here. Company finance configuration remains in the tenant workspace.</p></CardContent></Card></TabsContent>
      </Tabs>
    </>
  );
}
