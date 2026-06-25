import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronsLeftRight, LogOut, Moon, Search, Sun } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { superAdminApi } from "@/services/superAdminApi";
import { useAuth } from "@/hooks/useAuth";
import { useUiStore } from "@/store/uiStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { NotificationMenu } from "@/components/layout/NotificationMenu";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { SystemHealthIndicator } from "./SystemHealthIndicator";
import { SuperAdminMobileSidebar } from "./SuperAdminMobileSidebar";

export function SuperAdminTopbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { toggleSidebar, theme, setTheme } = useUiStore();
  const [search, setSearch] = useState("");
  const companies = useQuery({ queryKey: ["super-admin", "companies", "topbar"], queryFn: superAdminApi.getCompanies });
  const providers = useQuery({ queryKey: ["super-admin", "providers", "topbar"], queryFn: superAdminApi.getProviders });
  const results = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return [];
    return (companies.data ?? []).filter((company) => `${company.companyName} ${company.tenantId} ${company.adminEmail}`.toLowerCase().includes(term)).slice(0, 5);
  }, [companies.data, search]);
  const degraded = (providers.data ?? []).some((provider) => provider.status === "degraded" || provider.status === "outage");

  return (
    <header className="sticky top-0 z-20 flex min-h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-slate-800 dark:bg-navy-950/90 lg:px-6">
      <SuperAdminMobileSidebar />
      <Button variant="ghost" size="icon" onClick={toggleSidebar} className="hidden lg:inline-flex" aria-label="Toggle sidebar"><ChevronsLeftRight className="h-4 w-4" /></Button>
      <div className="hidden min-w-0 flex-1 flex-col gap-1 md:flex"><Breadcrumbs /></div>
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" placeholder="Search companies, tenant IDs, admins..." aria-label="Global company search" />
        {search && results.length ? (
          <div className="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-950">
            {results.map((company) => (
              <Link key={company.id} to={`/super-admin/companies/${company.id}`} onClick={() => setSearch("")} className="block border-b border-slate-100 px-4 py-3 last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900">
                <p className="text-sm font-semibold">{company.companyName}</p>
                <p className="mt-1 text-xs text-slate-500">{company.tenantId} · {company.adminEmail}</p>
              </Link>
            ))}
          </div>
        ) : null}
      </div>
      <Badge variant="brand" className="hidden lg:inline-flex">PRODUCTION</Badge>
      <SystemHealthIndicator degraded={degraded} />
      <Button variant="outline" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">{theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button>
      <NotificationMenu />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="gap-3 px-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 text-xs font-bold text-white">{user?.name?.slice(0, 2).toUpperCase() ?? "SA"}</span>
            <span className="hidden text-left text-sm xl:block"><span className="block font-semibold">{user?.name ?? "Platform admin"}</span><span className="block text-xs text-slate-500">SPECTRA AI Super Admin</span></span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onSelect={() => navigate("/super-admin/settings")}>Platform settings</DropdownMenuItem>
          <DropdownMenuItem onSelect={() => navigate("/app/dashboard")}>Open company workspace</DropdownMenuItem>
          <DropdownMenuItem onSelect={() => { logout(); navigate("/auth/login"); }}><LogOut className="mr-2 h-4 w-4" />Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
