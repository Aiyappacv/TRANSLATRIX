import type { ComponentType } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  BarChart3,
  Building2,
  Cable,
  CheckSquare,
  Circle,
  ClipboardCheck,
  Crown,
  Database,
  FileText,
  GitBranch,
  History,
  Languages,
  Layers3,
  LayoutDashboard,
  Link2,
  ListChecks,
  Palette,
  PlugZap,
  ReceiptText,
  Rocket,
  ScanLine,
  ScrollText,
  Send,
  Settings,
  ShieldAlert,
  ShieldCheck,
  TableProperties,
  UsersRound,
  Webhook,
} from "lucide-react";
import { navGroups } from "@/app/routeConfig";
import { usePermissions } from "@/hooks/usePermissions";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";
import { APP_NAME } from "@/utils/constants";
import { Badge } from "@/components/ui/badge";

const iconMap: Record<string, ComponentType<{ className?: string }>> = {
  BarChart3,
  Building2,
  Cable,
  CheckSquare,
  ClipboardCheck,
  Crown,
  FileText,
  GitBranch,
  History,
  Languages,
  Layers3,
  LayoutDashboard,
  Link2,
  ListChecks,
  Palette,
  PlugZap,
  ReceiptText,
  Rocket,
  ScanLine,
  ScrollText,
  Send,
  Settings,
  ShieldAlert,
  TableProperties,
  UsersRound,
  Webhook,
};

function NavIcon({ name }: { name: string }) {
  const Icon = iconMap[name] ?? Circle;
  return <Icon className="h-4 w-4" />;
}

export function AppSidebar() {
  const location = useLocation();
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const { hasAnyPermission } = usePermissions();

  return (
    <aside aria-label="Main navigation sidebar" className={cn("fixed left-0 top-0 z-30 hidden h-screen flex-col bg-navy-900 text-slate-300 transition-all duration-200 lg:flex", collapsed ? "w-[72px]" : "w-[240px]")}> 
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand-gradient text-sm font-black text-white">TP</div>
        {!collapsed ? <div><p className="text-sm font-bold text-white">{APP_NAME}</p><p className="text-xs text-slate-400">AI finance cockpit</p></div> : null}
      </div>
      <nav aria-label="Main navigation" className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        {navGroups.map((group) => {
          const items = group.items.filter((item) => hasAnyPermission(item.permissions));
          if (!items.length) return null;
          return (
            <div key={group.label} className="mb-5">
              {!collapsed ? <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{group.label}</p> : null}
              <div className="space-y-1">
                {items.map((item) => {
                  const [itemPath, itemSearch] = item.path.split("?");
                  const currentFull = location.pathname + location.search;
                  let active: boolean;
                  if (itemSearch) active = currentFull === item.path;
                  else if (location.search) active = false;
                  else if (itemPath === "/app/dashboard") active = location.pathname === itemPath;
                  else active = location.pathname === itemPath || location.pathname.startsWith(`${itemPath}/`);
                  return (
                    <div key={item.path}>
                      <Link to={item.path} title={collapsed ? item.label : undefined} className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors", active ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white", collapsed && "justify-center px-2")}>
                        <NavIcon name={item.icon} />
                        {!collapsed ? <span className="flex-1 truncate">{item.label}</span> : null}
                        {!collapsed && item.badge ? <Badge variant="brand">{item.badge}</Badge> : null}
                      </Link>
                      {!collapsed && item.children && item.children.length > 0 && (
                        <div className="ml-4 mt-1 space-y-1 border-l border-white/10 pl-3">
                          {item.children.map((child) => {
                            const [childPath, childSearch] = child.path.split("?");
                            let childActive: boolean;
                            if (childSearch) childActive = currentFull === child.path;
                            else if (location.search) childActive = false;
                            else childActive = location.pathname === childPath || location.pathname.startsWith(`${childPath}/`);
                            return (
                              <Link key={child.path} to={child.path} className={cn("flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium transition-colors", childActive ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white")}>
                                <NavIcon name={child.icon} />
                                <span className="flex-1 truncate">{child.label}</span>
                                {child.badge ? <Badge variant="brand">{child.badge}</Badge> : null}
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className={cn("rounded-2xl border border-white/10 bg-white/5 p-3", collapsed && "p-2 text-center")}> 
          {!collapsed ? <><p className="text-xs font-semibold text-white">Production guardrails</p><p className="mt-1 text-xs leading-5 text-slate-400">Tenant isolated · MFA · idempotent SAP posting</p></> : <ShieldCheck className="mx-auto h-5 w-5" />}
        </div>
      </div>
    </aside>
  );
}
