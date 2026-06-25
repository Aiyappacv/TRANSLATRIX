import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import type { SecuritySettings } from "@/types";
import { securitySettingsSchema } from "@/schemas/settings.schema";
import { settingsApi } from "@/services/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { SettingsFormActions } from "@/components/settings/SettingsFormActions";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/useToast";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";

export function SecuritySettingsPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["settings", "security"], queryFn: settingsApi.getSecuritySettings });
  const form = useForm<SecuritySettings>({ resolver: zodResolver(securitySettingsSchema), defaultValues: query.data });
  useEffect(() => { if (query.data) form.reset(query.data); }, [form, query.data]);
  useUnsavedChanges(form.formState.isDirty);
  const save = useMutation({ mutationFn: settingsApi.saveSecuritySettings, onSuccess: (data) => { form.reset(data); toast.success("Security settings saved", "New sessions and access checks will use the updated policy."); }, onError: (error) => toast.error("Unable to save security settings", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading security settings..." />;
  if (query.isError) return <ErrorState title="Security settings unavailable" description="Security policy could not be loaded." onRetry={() => query.refetch()} />;
  return <form className="space-y-6" onSubmit={form.handleSubmit((value) => save.mutate(value))}>
    <PageHeader eyebrow="Phase 12 · Administration" title="Security settings" description="MFA, password policy, sessions, IP restrictions, SSO placeholder, and audit retention." actions={<Badge variant={form.watch("mfaRequired") || form.watch("mfaRequiredForPrivilegedRoles") ? "success" : "warning"}>{form.watch("mfaRequired") || form.watch("mfaRequiredForPrivilegedRoles") ? "MFA enforced" : "MFA not enforced"}</Badge>} />
    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardHeader><CardTitle>Authentication and sessions</CardTitle><CardDescription>Controls for tenant users and privileged finance roles.</CardDescription></CardHeader><CardContent className="space-y-5">
        <Controller control={form.control} name="mfaRequired" render={({ field }) => <Switch label="Require MFA for all users" checked={field.value} onCheckedChange={field.onChange} />} />
        <Controller control={form.control} name="mfaRequiredForPrivilegedRoles" render={({ field }) => <Switch label="Require MFA for privileged roles" checked={field.value} onCheckedChange={field.onChange} />} />
        <div className="space-y-2"><Label>Session timeout (minutes)</Label><Input type="number" {...form.register("sessionTimeoutMinutes")} /></div>
        <div className="space-y-2"><Label>Password expiry (days, 0 = never)</Label><Input type="number" {...form.register("passwordExpiryDays")} /></div>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Password policy</CardTitle><CardDescription>Applied to local accounts when SSO is not enabled.</CardDescription></CardHeader><CardContent className="space-y-4">
        <div className="space-y-2"><Label>Minimum password length</Label><Input type="number" {...form.register("passwordMinimumLength")} /></div>
        {(["passwordRequireUppercase", "passwordRequireLowercase", "passwordRequireNumber", "passwordRequireSymbol"] as const).map((name) => <Controller key={name} control={form.control} name={name} render={({ field }) => <Switch label={name.replace("passwordRequire", "Require ").replace("Uppercase", "uppercase").replace("Lowercase", "lowercase").replace("Number", "number").replace("Symbol", "symbol")} checked={field.value} onCheckedChange={field.onChange} />} />)}
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Network and SSO</CardTitle><CardDescription>IP restrictions are evaluated by the backend gateway.</CardDescription></CardHeader><CardContent className="space-y-5">
        <div className="space-y-2"><Label>Allowed IP ranges</Label><Textarea className="min-h-32 font-mono" {...form.register("allowedIpRanges")} /></div>
        <Controller control={form.control} name="ssoEnabled" render={({ field }) => <Switch label="Enable SSO placeholder" checked={field.value} onCheckedChange={field.onChange} />} />
        <div className="space-y-2"><Label>SSO provider</Label><Input {...form.register("ssoProvider")} /></div>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Audit retention</CardTitle><CardDescription>Retention must satisfy legal, accounting, and internal policy requirements.</CardDescription></CardHeader><CardContent className="space-y-3"><Label>Audit retention (days)</Label><Input type="number" {...form.register("auditRetentionDays")} /><p className="text-sm text-slate-500">Current policy keeps immutable audit evidence for approximately {Math.round((form.watch("auditRetentionDays") || 0) / 365)} years.</p></CardContent></Card>
    </div>
    <SettingsFormActions dirty={form.formState.isDirty} saving={save.isPending} onCancel={() => form.reset(query.data)} />
  </form>;
}
