import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { PlatformSettings } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/useToast";

export function SuperAdminSettingsPage() {
  const toast = useToast();
  const settings = useQuery({ queryKey: ["super-admin", "settings"], queryFn: superAdminApi.getSettings });
  const [form, setForm] = useState<PlatformSettings | null>(null);
  useEffect(() => { if (settings.data) setForm(settings.data); }, [settings.data]);
  const save = useMutation({ mutationFn: superAdminApi.saveSettings, onSuccess: () => toast.success("Platform settings saved", "Changes were recorded in the Super Admin audit log.") });
  if (settings.isLoading || !form) return <LoadingState label="Loading platform settings..." />;
  return (
    <>
      <PageHeader eyebrow="Platform configuration" title="Super Admin settings" description="Control production environment safeguards, audited support access, retention, operational thresholds, and notification destinations." actions={<Button disabled={save.isPending} onClick={() => save.mutate(form)}>Save settings</Button>} />
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Environment and access</CardTitle><CardDescription>High-impact controls should require step-up authentication in the backend.</CardDescription></CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2"><Label>Environment</Label><Select value={form.environment} onValueChange={(value: PlatformSettings["environment"]) => setForm({ ...form, environment: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="production">Production</SelectItem><SelectItem value="staging">Staging</SelectItem></SelectContent></Select></div>
            <Switch label="Maintenance mode" checked={form.maintenanceMode} onChange={(event) => setForm({ ...form, maintenanceMode: event.target.checked })} />
            <Switch label="Enable audited tenant support access" checked={form.tenantImpersonationEnabled} onChange={(event) => setForm({ ...form, tenantImpersonationEnabled: event.target.checked })} />
            <Switch label="Require an audit reason before tenant access" checked={form.requireAuditReason} onChange={(event) => setForm({ ...form, requireAuditReason: event.target.checked })} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Capacity and governance</CardTitle><CardDescription>Defaults used when provisioning new tenants and alerting platform operators.</CardDescription></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2"><Label htmlFor="trialDays">Default trial days</Label><Input id="trialDays" type="number" value={form.defaultTrialDays} onChange={(event) => setForm({ ...form, defaultTrialDays: Number(event.target.value) })} /></div>
            <div className="space-y-2"><Label htmlFor="retention">Audit retention days</Label><Input id="retention" type="number" value={form.dataRetentionDays} onChange={(event) => setForm({ ...form, dataRetentionDays: Number(event.target.value) })} /></div>
            <div className="space-y-2"><Label htmlFor="threshold">Queue alert threshold</Label><Input id="threshold" type="number" value={form.queueAlertThreshold} onChange={(event) => setForm({ ...form, queueAlertThreshold: Number(event.target.value) })} /></div>
            <div className="space-y-2"><Label htmlFor="alertEmail">Error alert email</Label><Input id="alertEmail" type="email" value={form.errorAlertEmail} onChange={(event) => setForm({ ...form, errorAlertEmail: event.target.value })} /></div>
            <div className="space-y-2"><Label htmlFor="supportEmail">Support email</Label><Input id="supportEmail" type="email" value={form.supportEmail} onChange={(event) => setForm({ ...form, supportEmail: event.target.value })} /></div>
            <div className="space-y-2"><Label htmlFor="statusUrl">Status page URL</Label><Input id="statusUrl" type="url" value={form.statusPageUrl} onChange={(event) => setForm({ ...form, statusPageUrl: event.target.value })} /></div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
