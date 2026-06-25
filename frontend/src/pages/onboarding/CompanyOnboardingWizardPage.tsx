import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormProvider, useForm, useFormContext, type FieldPath } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Save, ShieldCheck } from "lucide-react";
import { onboardingApi } from "@/services/onboardingApi";
import { onboardingDraftSchema, onboardingIntegrations, onboardingRoles, type OnboardingDraftInput } from "@/schemas/onboarding.schema";
import { useTenantStore } from "@/store/tenantStore";
import { PageHeader } from "@/components/common/PageHeader";
import { MultiStepWizard } from "@/components/onboarding/MultiStepWizard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";

const steps = ["Company profile", "Finance configuration", "User invitations", "Integration selection", "Security settings", "Review and submit"];

const defaults: OnboardingDraftInput = {
  companyProfile: {
    legalName: "",
    tradingName: "",
    country: "",
    industry: "",
    registrationNumber: "",
    taxId: "",
    primaryContactName: "",
    primaryContactEmail: "",
    phoneNumber: "",
    website: "",
    defaultCurrency: "",
    defaultLanguage: "",
    timezone: "",
  },
  finance: {
    companyCode: "",
    fiscalYearVariant: "",
    baseCurrency: "",
    taxCountry: "",
    approvalPolicy: "",
  },
  invitations: onboardingRoles.map((role) => ({ role, email: "" })),
  integrations: [],
  security: { mfaRequired: false, ssoEnabled: false, ipRestrictions: "" },
};

const stepFields: Array<Array<keyof OnboardingDraftInput | `companyProfile.${keyof OnboardingDraftInput["companyProfile"]}` | `finance.${keyof OnboardingDraftInput["finance"]}` | "invitations" | "integrations" | `security.${keyof OnboardingDraftInput["security"]}`>> = [
  ["companyProfile.legalName", "companyProfile.tradingName", "companyProfile.country", "companyProfile.industry", "companyProfile.registrationNumber", "companyProfile.taxId", "companyProfile.primaryContactName", "companyProfile.primaryContactEmail", "companyProfile.phoneNumber", "companyProfile.website", "companyProfile.defaultCurrency", "companyProfile.defaultLanguage", "companyProfile.timezone"],
  ["finance.companyCode", "finance.fiscalYearVariant", "finance.baseCurrency", "finance.taxCountry", "finance.approvalPolicy"],
  ["invitations"],
  ["integrations"],
  ["security.mfaRequired", "security.ssoEnabled", "security.ipRestrictions"],
  [],
];

function FormField({ label, name, type = "text" }: { label: string; name: FieldPath<OnboardingDraftInput>; type?: string }) {
  const form = useFormContext<OnboardingDraftInput>();
  const error = name.split(".").reduce<unknown>((value, key) => (value && typeof value === "object" ? (value as Record<string, unknown>)[key] : undefined), form.formState.errors) as { message?: string } | undefined;
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} type={type} {...form.register(name)} />
      {error?.message ? <p className="text-xs text-danger">{error.message}</p> : null}
    </div>
  );
}

export function CompanyOnboardingWizardPage() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const navigate = useNavigate();
  const toast = useToast();
  const activateUserCompany = useTenantStore((state) => state.activateUserCompany);
  const draftQuery = useQuery({ queryKey: ["onboarding-draft"], queryFn: onboardingApi.getDraft });
  const form = useForm<OnboardingDraftInput>({ resolver: zodResolver(onboardingDraftSchema), defaultValues: defaults, mode: "onBlur" });

  useEffect(() => {
    if (draftQuery.data) form.reset(draftQuery.data);
  }, [draftQuery.data, form]);

  const saveMutation = useMutation({
    mutationFn: onboardingApi.saveDraft,
    onSuccess: (result) => toast.success("Onboarding draft saved", `Saved ${new Date(result.savedAt).toLocaleTimeString()}`),
    onError: (error) => toast.error("Draft could not be saved", error instanceof Error ? error.message : "Unknown error"),
  });
  const submitMutation = useMutation({
    mutationFn: onboardingApi.submit,
    onSuccess: (result) => {
      activateUserCompany(result.company);
      toast.success("Company onboarding completed", `${result.company.name} is now the active tenant context.`);
      navigate("/app/onboarding/complete", { replace: true, state: result.company });
    },
    onError: (error) => toast.error("Onboarding submission failed", error instanceof Error ? error.message : "Unknown error"),
  });

  const values = form.watch();
  const completedInvites = values.invitations.filter((item) => item.email.trim()).length;
  const reviewItems = useMemo(() => [
    ["Company", values.companyProfile.legalName],
    ["Primary contact", `${values.companyProfile.primaryContactName} · ${values.companyProfile.primaryContactEmail}`],
    ["Company code", values.finance.companyCode],
    ["Approval policy", values.finance.approvalPolicy],
    ["Invitations", `${completedInvites} prepared`],
    ["Integrations", values.integrations.join(", ")],
    ["Security", `${values.security.mfaRequired ? "MFA required" : "MFA optional"}${values.security.ssoEnabled ? " · SSO enabled" : ""}`],
  ], [completedInvites, values]);

  const next = async () => {
    const fields = stepFields[currentIndex];
    const valid = fields.length ? await form.trigger(fields as Parameters<typeof form.trigger>[0], { shouldFocus: true }) : true;
    if (!valid) return;
    if (currentIndex < steps.length - 1) setCurrentIndex((index) => index + 1);
    else await form.handleSubmit((payload) => submitMutation.mutate(payload))();
  };

  const renderStep = (index: number) => (
    <Card>
      <CardHeader><CardTitle>{steps[index]}</CardTitle><CardDescription>Tenant-scoped configuration is validated before you continue.</CardDescription></CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        {index === 0 ? <>
          <FormField label="Company legal name" name="companyProfile.legalName" /><FormField label="Trading name" name="companyProfile.tradingName" />
          <FormField label="Country" name="companyProfile.country" /><FormField label="Industry" name="companyProfile.industry" />
          <FormField label="Company registration number" name="companyProfile.registrationNumber" /><FormField label="Tax/VAT/GST number" name="companyProfile.taxId" />
          <FormField label="Primary contact name" name="companyProfile.primaryContactName" /><FormField label="Primary contact email" name="companyProfile.primaryContactEmail" type="email" />
          <FormField label="Phone number" name="companyProfile.phoneNumber" /><FormField label="Website" name="companyProfile.website" type="url" />
          <FormField label="Default currency" name="companyProfile.defaultCurrency" /><FormField label="Default language" name="companyProfile.defaultLanguage" />
          <FormField label="Timezone" name="companyProfile.timezone" />
        </> : null}
        {index === 1 ? <>
          <FormField label="Default company code" name="finance.companyCode" /><FormField label="Fiscal year variant" name="finance.fiscalYearVariant" />
          <FormField label="Base currency" name="finance.baseCurrency" /><FormField label="Tax country" name="finance.taxCountry" />
          <div className="md:col-span-2"><FormField label="Approval policy" name="finance.approvalPolicy" /></div>
        </> : null}
        {index === 2 ? values.invitations.map((invite, inviteIndex) => (
          <div key={invite.role} className="space-y-2"><Label htmlFor={`invite-${inviteIndex}`}>{invite.role}</Label><Input id={`invite-${inviteIndex}`} type="email" {...form.register(`invitations.${inviteIndex}.email`)} /><input type="hidden" {...form.register(`invitations.${inviteIndex}.role`)} /></div>
        )) : null}
        {index === 3 ? <div className="grid gap-3 md:col-span-2 sm:grid-cols-2">{onboardingIntegrations.map((integration) => {
          const checked = values.integrations.includes(integration);
          return <Checkbox key={integration} label={integration} checked={checked} onChange={(event) => form.setValue("integrations", event.target.checked ? [...values.integrations, integration] : values.integrations.filter((item) => item !== integration), { shouldDirty: true, shouldValidate: true })} />;
        })}{form.formState.errors.integrations?.message ? <p className="text-xs text-danger sm:col-span-2">{form.formState.errors.integrations.message}</p> : null}</div> : null}
        {index === 4 ? <div className="space-y-4 md:col-span-2">
          <Switch label="MFA required" checked={values.security.mfaRequired} onChange={(event) => form.setValue("security.mfaRequired", event.target.checked, { shouldDirty: true })} />
          <Switch label="Enable SSO placeholder" checked={values.security.ssoEnabled} onChange={(event) => form.setValue("security.ssoEnabled", event.target.checked, { shouldDirty: true })} />
          <FormField label="Allowed IP ranges (placeholder)" name="security.ipRestrictions" />
          <Alert tone="info"><ShieldCheck className="mr-2 inline h-4 w-4" />Security settings are tenant-scoped and included in the audit trail.</Alert>
        </div> : null}
        {index === 5 ? <div className="space-y-4 md:col-span-2">
          <Alert tone="success"><CheckCircle2 className="mr-2 inline h-4 w-4" />Review all details before activating the tenant.</Alert>
          <dl className="grid gap-3 sm:grid-cols-2">{reviewItems.map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 text-sm font-semibold">{value}</dd></div>)}</dl>
        </div> : null}
      </CardContent>
    </Card>
  );

  return (
    <FormProvider {...form}>
      <PageHeader eyebrow="Phase 3" title="Company onboarding wizard" description="Six validated steps for company profile, finance setup, invitations, integrations, security, and tenant activation." actions={<Button type="button" variant="outline" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(form.getValues())}><Save className="h-4 w-4" />Save draft</Button>} />
      <MultiStepWizard steps={steps} currentIndex={currentIndex} renderStep={renderStep} onBack={() => setCurrentIndex((index) => Math.max(0, index - 1))} onNext={next} busy={submitMutation.isPending} />
    </FormProvider>
  );
}
