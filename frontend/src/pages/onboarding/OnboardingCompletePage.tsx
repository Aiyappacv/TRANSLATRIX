import { Link, useLocation } from "react-router-dom";
import { Building2, CheckCircle2, ShieldCheck } from "lucide-react";
import type { TenantCompanyOption } from "@/store/tenantStore";
import { useTenantStore } from "@/store/tenantStore";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function OnboardingCompletePage() {
  const location = useLocation();
  const stateCompany = location.state as TenantCompanyOption | null;
  const activeCompanyId = useTenantStore((state) => state.activeCompanyId);
  const activeCompanyName = useTenantStore((state) => state.activeCompanyName);
  const company = stateCompany ?? (activeCompanyId && activeCompanyName ? { id: activeCompanyId, name: activeCompanyName, tenantId: useTenantStore.getState().activeTenantId ?? "" } : null);

  return (
    <Card>
      <CardContent className="p-12 text-center">
        <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-success" />
        <h1 className="text-2xl font-bold">Onboarding complete</h1>
        <p className="mt-2 text-slate-500">Company profile, finance setup, users, integrations, and security settings are ready.</p>
        {company ? <div className="mx-auto mt-6 max-w-lg rounded-2xl border border-success/20 bg-success/10 p-4 text-left"><div className="flex items-center gap-3"><Building2 className="h-5 w-5 text-success" /><div className="min-w-0 flex-1"><p className="truncate font-semibold">{company.name}</p><p className="text-xs text-slate-500">Tenant {company.tenantId} · Company {company.id}</p></div><Badge variant="success"><ShieldCheck className="mr-1 h-3 w-3" />Active tenant</Badge></div></div> : null}
        <Button asChild className="mt-6"><Link to="/app/dashboard">Go to dashboard</Link></Button>
      </CardContent>
    </Card>
  );
}
