import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { Building2, CheckCircle2 } from "lucide-react";
import { companyApi } from "@/services/companyApi";
import { registerCompanySchema, type RegisterCompanyInput } from "@/schemas/company.schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/useToast";

const defaults: RegisterCompanyInput = {
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
  preferredAccountingSystem: "",
};

const fields: Array<keyof RegisterCompanyInput> = ["legalName", "tradingName", "country", "industry", "registrationNumber", "taxId", "primaryContactName", "primaryContactEmail", "phoneNumber", "website", "defaultCurrency", "defaultLanguage", "timezone", "preferredAccountingSystem"];

export function RegisterCompanyPage() {
  const toast = useToast();
  const form = useForm<RegisterCompanyInput>({ resolver: zodResolver(registerCompanySchema), defaultValues: defaults });
  const mutation = useMutation({
    mutationFn: companyApi.register,
    onSuccess: () => toast.success("Company registration submitted", "Tenant pending verification; onboarding will open after approval"),
    onError: (error) => toast.error("Registration failed", error instanceof Error ? error.message : "Unable to register the company"),
  });

  return (
    <Card className="shadow-enterprise">
      <CardHeader>
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient text-white"><Building2 className="h-5 w-5" /></div>
        <CardTitle className="text-2xl">Register company</CardTitle>
        <CardDescription>Create the tenant, admin user, company defaults, and first accounting integration preference.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit((input) => mutation.mutate(input))} className="grid gap-4 md:grid-cols-2">
          {fields.map((field) => (
            <div key={field} className="space-y-2">
              <Label htmlFor={field}>{field.replace(/([A-Z])/g, " $1").replace(/^./, (s) => s.toUpperCase())}</Label>
              <Input id={field} {...form.register(field)} />
              {form.formState.errors[field] ? <p className="text-xs text-danger">{form.formState.errors[field]?.message}</p> : null}
            </div>
          ))}
          <div className="md:col-span-2">
            <Button type="submit" disabled={mutation.isPending}>{mutation.isSuccess ? <CheckCircle2 className="h-4 w-4" /> : null} Submit registration</Button>
          </div>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">Already approved? <Link className="font-semibold text-primary" to="/auth/login">Sign in</Link></p>
      </CardContent>
    </Card>
  );
}
