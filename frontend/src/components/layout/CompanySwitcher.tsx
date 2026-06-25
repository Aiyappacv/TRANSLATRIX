import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, Check } from "lucide-react";
import { companyApi } from "@/services/companyApi";
import { useAuthStore } from "@/store/authStore";
import { useTenantStore, type TenantCompanyOption } from "@/store/tenantStore";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export function CompanySwitcher() {
  const user = useAuthStore((state) => state.user);
  const activeCompanyId = useTenantStore((state) => state.activeCompanyId);
  const activeCompanyName = useTenantStore((state) => state.activeCompanyName);
  const availableCompanies = useTenantStore((state) => state.availableCompanies);
  const activateUserCompany = useTenantStore((state) => state.activateUserCompany);
  const setAvailableCompanies = useTenantStore((state) => state.setAvailableCompanies);
  const setActiveCompany = useTenantStore((state) => state.setActiveCompany);

  const companiesQuery = useQuery({
    queryKey: ["company-switcher-options"],
    queryFn: companyApi.getCompanies,
    enabled: Boolean(user?.canSwitchCompanies),
  });

  useEffect(() => {
    if (!user) return;
    if (!activeCompanyId || (!user.canSwitchCompanies && activeCompanyId !== user.companyId)) {
      activateUserCompany({ id: user.companyId, name: user.companyName, tenantId: user.tenantId });
    }
  }, [activateUserCompany, activeCompanyId, user]);

  useEffect(() => {
    if (!companiesQuery.data) return;
    setAvailableCompanies(companiesQuery.data.map<TenantCompanyOption>((company) => ({
      id: company.id,
      name: company.tradingName || company.legalName,
      tenantId: company.tenantId,
    })));
  }, [companiesQuery.data, setAvailableCompanies]);

  const visible = useMemo(() => {
    if (!user) return [];
    if (user.canSwitchCompanies) return availableCompanies;
    return availableCompanies.filter((company) => company.id === user.companyId);
  }, [availableCompanies, user]);

  const displayName = user?.canSwitchCompanies ? (activeCompanyName ?? user.companyName) : user?.companyName;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="hidden max-w-44 gap-1.5 lg:inline-flex"><Building2 className="h-4 w-4 shrink-0" /><span className="truncate">{displayName ?? "Company"}</span></Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        {visible.length ? visible.map((company) => <DropdownMenuItem key={company.id} onSelect={() => setActiveCompany(company)} className="justify-between"><span>{company.name}</span>{activeCompanyId === company.id ? <Check className="h-4 w-4 text-success" /> : null}</DropdownMenuItem>) : <DropdownMenuItem disabled>No companies available</DropdownMenuItem>}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
