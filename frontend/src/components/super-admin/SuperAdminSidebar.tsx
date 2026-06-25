import type { ComponentType } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  BadgeDollarSign,
  Building2,
  ChartNoAxesCombined,
  Circle,
  CreditCard,
  LayoutDashboard,
  LifeBuoy,
  ListTodo,
  Network,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { superAdminNavGroups } from "@/app/superAdminRouteConfig";
import { usePermissions } from "@/hooks/usePermissions";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";
import { Badge } from "@/components/ui/badge";

const iconMap: Record<string, ComponentType<{ className?: string }>> = {
  Activity,
  BadgeDollarSign,
  Building2,
  ChartNoAxesCombined,
  CreditCard,
  LayoutDashboard,
  LifeBuoy,
  ListTodo,
  Network,
  ScrollText,
  Settings,
  ShieldAlert,
};

export function SuperAdminSidebar() {
  const location = useLocation();
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const { hasPermission } = usePermissions();

  return (
    <aside aria-label="Platform navigation sidebar" className={cn("fixed left-0 top-0 z-30 hidden h-screen flex-col border-r border-white/10 bg-[#071426] text-slate-300 transition-all duration-200 lg:flex", collapsed ? "w-[72px]" : "w-[240px]")}>
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 text-sm font-black text-white">SA</div>
        {!collapsed ? <div><p className="text-sm font-bold text-white">SPECTRA AI</p><p className="text-xs text-slate-400">Platform administration</p></div> : null}
      </div>
      <nav aria-label="Platform navigation" className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        {superAdminNavGroups.map((group) => {
          const items = group.items.filter((item) => hasPermission(item.permission));
          if (!items.length) return null;
          return (
            <div key={group.label} className="mb-5">
              {!collapsed ? <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{group.label}</p> : null}
              <div className="space-y-1">
                {items.map((item) => {
                  const Icon = iconMap[item.icon] ?? Circle;
                  const active = location.pathname === item.path || (item.path !== "/super-admin/dashboard" && location.pathname.startsWith(`${item.path}/`));
                  return (
                    <Link key={item.path} to={item.path} title={collapsed ? item.label : undefined} className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors", active ? "bg-white/10 text-white shadow-inner" : "hover:bg-white/5 hover:text-white", collapsed && "justify-center px-2")}>
                      <Icon className="h-4 w-4 shrink-0" />
                      {!collapsed ? <span className="flex-1 truncate">{item.label}</span> : null}
                      {!collapsed && item.badge ? <Badge variant={active ? "brand" : "neutral"} className="border-white/10 bg-white/10 text-slate-200">{item.badge}</Badge> : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className={cn("rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-3", collapsed && "p-2 text-center")}>
          {!collapsed ? <><p className="flex items-center gap-2 text-xs font-semibold text-emerald-300"><ShieldCheck className="h-4 w-4" />Audited admin mode</p><p className="mt-1 text-xs leading-5 text-slate-400">Tenant access and platform actions are fully traceable.</p></> : <ShieldCheck className="mx-auto h-5 w-5 text-emerald-300" />}
        </div>
      </div>
    </aside>
  );
}
