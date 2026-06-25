import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Building2, CheckCircle2, ExternalLink, Loader2, ShieldCheck } from "lucide-react";
import type { PlatformCompanyProvisioningInput } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";

const initialForm: PlatformCompanyProvisioningInput = {
  legalName: "",
  adminEmail: "",
  country: "India",
  industry: "",
  plan: "Growth",
  defaultCurrency: "INR",
  companyCode: "",
  timezone: "Asia/Kolkata",
  requireMfa: false,
  allowAuditedSupportAccess: true,
};

export function SuperAdminCompanyOnboardingPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<PlatformCompanyProvisioningInput>(initialForm);
  const [activationPath, setActivationPath] = useState("");
  const registrations = useQuery({ queryKey: ["super-admin", "registration-requests"], queryFn: superAdminApi.getRegistrationRequests });
  const approveRegistration = useMutation({
    mutationFn: superAdminApi.approveRegistrationRequest,
    onSuccess: async (result) => {
      setActivationPath(result.activationPath);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["super-admin", "registration-requests"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "companies"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] }),
      ]);
      toast.success("Tenant registration approved", `${result.company.companyName} can now activate the Company Admin account.`);
    },
    onError: (error) => toast.error("Registration approval failed", error instanceof Error ? error.message : "Unable to approve the tenant registration."),
  });
  const provision = useMutation({
    mutationFn: superAdminApi.createCompany,
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["super-admin", "companies"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "subscriptions"] }),
        queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] }),
      ]);
      toast.success("Tenant provisioned", `${result.company.companyName} created successfully. Job ${result.jobId}.`);
      navigate(`/super-admin/companies/${result.company.id}`);
    },
    onError: (error) => toast.error("Tenant provisioning failed", error instanceof Error ? error.message : "Unable to provision company."),
  });

  const update = <K extends keyof PlatformCompanyProvisioningInput>(key: K, value: PlatformCompanyProvisioningInput[K]) => setForm((current) => ({ ...current, [key]: value }));
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.legalName.trim() || !form.industry.trim() || !form.country.trim() || !form.companyCode.trim()) {
      toast.error("Complete required company fields", "Legal name, country, industry, and company code are required.");
      return;
    }
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(form.adminEmail.trim())) {
      toast.error("Enter a valid company admin email");
      return;
    }
    provision.mutate(form);
  };

  return (
    <>
      <PageHeader eyebrow="Tenant provisioning" title="Company onboarding" description="Approve submitted registrations or directly create a client company with baseline security controls." badge="Audited" />
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Pending company registrations</CardTitle>
          <CardDescription>Public registrations remain inactive until a Super Admin approves them. Approval creates a one-time activation path for the Company Admin.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {activationPath ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">
              <p className="font-semibold">Company Admin activation path</p>
              <p className="mt-1 break-all font-mono text-xs">{activationPath}</p>
              <Button asChild variant="outline" size="sm" className="mt-3"><a href={activationPath}><ExternalLink className="h-4 w-4" />Open activation</a></Button>
            </div>
          ) : null}
          {registrations.isLoading ? <p className="text-sm text-slate-500">Loading registration requests...</p> : null}
          {registrations.isError ? <p className="text-sm text-red-600">Registration requests could not be loaded.</p> : null}
          {!registrations.isLoading && !registrations.isError && (registrations.data ?? []).filter((item) => item.status === "pending").length === 0 ? <p className="text-sm text-slate-500">No company registrations are awaiting approval.</p> : null}
          {(registrations.data ?? []).filter((item) => item.status === "pending").map((item) => (
            <div key={item.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold">{item.companyName}</p>
                <p className="text-sm text-slate-500">{item.adminEmail} · {item.country || "Country not provided"} · {item.industry || "Industry not provided"}</p>
              </div>
              <Button size="sm" disabled={approveRegistration.isPending} onClick={() => approveRegistration.mutate(item.id)}>{approveRegistration.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}Approve and activate</Button>
            </div>
          ))}
        </CardContent>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader><CardTitle>Provision company tenant</CardTitle><CardDescription>Submission creates a persisted tenant record, subscription allocation, Company Admin invitation baseline, audit event, and traceable provisioning job ID.</CardDescription></CardHeader>
          <CardContent>
            <form className="grid gap-5 md:grid-cols-2" onSubmit={submit}>
              <div className="space-y-2"><Label htmlFor="legalName">Legal company name</Label><Input id="legalName" required value={form.legalName} onChange={(event) => update("legalName", event.target.value)} placeholder="Legal company name" /></div>
              <div className="space-y-2"><Label htmlFor="adminEmail">Company admin email</Label><Input id="adminEmail" required type="email" value={form.adminEmail} onChange={(event) => update("adminEmail", event.target.value)} placeholder="Company admin email" /></div>
              <div className="space-y-2"><Label htmlFor="country">Country</Label><Input id="country" required value={form.country} onChange={(event) => update("country", event.target.value)} placeholder="Country" /></div>
              <div className="space-y-2"><Label htmlFor="industry">Industry</Label><Input id="industry" required value={form.industry} onChange={(event) => update("industry", event.target.value)} placeholder="Industry" /></div>
              <div className="space-y-2"><Label>Subscription plan</Label><Select value={form.plan} onValueChange={(value) => update("plan", value as PlatformCompanyProvisioningInput["plan"])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Starter">Starter</SelectItem><SelectItem value="Growth">Growth</SelectItem><SelectItem value="Enterprise">Enterprise</SelectItem></SelectContent></Select></div>
              <div className="space-y-2"><Label htmlFor="currency">Default currency</Label><Input id="currency" required value={form.defaultCurrency} onChange={(event) => update("defaultCurrency", event.target.value.toUpperCase())} /></div>
              <div className="space-y-2"><Label htmlFor="companyCode">Default company code</Label><Input id="companyCode" required value={form.companyCode} onChange={(event) => update("companyCode", event.target.value.toUpperCase())} placeholder="Company code" /></div>
              <div className="space-y-2"><Label htmlFor="timezone">Timezone</Label><Input id="timezone" required value={form.timezone} onChange={(event) => update("timezone", event.target.value)} /></div>
              <div className="md:col-span-2 grid gap-3 rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                <Switch label="Require MFA for every tenant user" checked={form.requireMfa} onChange={(event) => update("requireMfa", event.target.checked)} />
                <Switch label="Allow audited Super Admin support access" checked={form.allowAuditedSupportAccess} onChange={(event) => update("allowAuditedSupportAccess", event.target.checked)} />
              </div>
              <div className="md:col-span-2 flex justify-end"><Button type="submit" disabled={provision.isPending}>{provision.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Building2 className="h-4 w-4" />}{provision.isPending ? "Provisioning..." : "Start provisioning"}</Button></div>
            </form>
          </CardContent>
        </Card>
        <div className="space-y-4">
          <Card><CardHeader><CardTitle className="text-base">Provisioning guardrails</CardTitle></CardHeader><CardContent className="space-y-3 text-sm text-slate-600 dark:text-slate-300">{["Unique tenant and company identifiers", "Dedicated encryption context", "Company Admin invitation", "Usage meter allocation", "Default integration policy", "Immutable audit baseline"].map((item) => <p key={item} className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-500" />{item}</p>)}</CardContent></Card>
          <Card><CardContent className="flex gap-3 p-5"><ShieldCheck className="h-5 w-5 text-primary" /><p className="text-sm leading-6 text-slate-500">No finance documents are visible from onboarding. Tenant support access must be separately authorized and audited.</p></CardContent></Card>
        </div>
      </div>
    </>
  );
}
