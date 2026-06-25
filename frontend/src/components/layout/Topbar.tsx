import { ChevronsLeftRight, LogOut, Moon, Sun } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/useAuth";
import { useUiStore } from "@/store/uiStore";
import { roleLabels } from "@/utils/permissions";
import { dashboardRolePaths } from "@/utils/dashboardRoles";
import { CompanySwitcher } from "./CompanySwitcher";
import { QuickActionsPanel } from "./QuickActionsPanel";
import { MobileSidebarDrawer } from "./MobileSidebarDrawer";
import { GlobalSearch } from "./GlobalSearch";
import { NotificationMenu } from "./NotificationMenu";
import { cn } from "@/utils/cn";
import { useAuthStore } from "@/store/authStore";

export function Topbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { toggleSidebar, theme, setTheme } = useUiStore();
  const activeRole = useAuthStore((state) => state.activeRole);
  const setActiveRole = useAuthStore((state) => state.setActiveRole);
  const role = activeRole ?? user?.roles?.[0];
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/85 px-3 backdrop-blur dark:border-slate-800 dark:bg-navy-950/85 lg:px-4">
      <MobileSidebarDrawer />
      <Button variant="ghost" size="icon" onClick={toggleSidebar} className="hidden h-9 w-9 lg:inline-flex" aria-label="Toggle sidebar"><ChevronsLeftRight className="h-4 w-4" /></Button>
      <CompanySwitcher />
      <div className="hidden flex-1 md:flex"><GlobalSearch /></div>
      <nav aria-label="Primary workspace" className="hidden items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 xl:flex dark:border-slate-800 dark:bg-slate-900">
        {[
          { label: "Dashboard", to: "/app/dashboard" },
          { label: "Company profile", to: "/app/settings/company" },
          { label: "Processing", to: "/app/entries" },
        ].map((item) => (
          <NavLink
            key={item.label}
            to={item.to}
            className={({ isActive }) => cn(
              "rounded-lg px-3 py-1.5 text-xs font-semibold transition",
              isActive ? "bg-white text-primary shadow-sm dark:bg-slate-800" : "text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white",
            )}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-1"><QuickActionsPanel />
        {user?.isPlatformOwner ? <Badge variant="brand" className="text-[10px] leading-none px-1.5 py-0.5">Platform owner</Badge> : null}
        <Button variant="outline" size="icon" className="h-9 w-9" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">{theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</Button>
        <NotificationMenu />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-1.5 px-1.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-gradient text-xs font-bold text-white">{user?.name?.slice(0, 2).toUpperCase() ?? "TP"}</span>
              <span className="hidden text-left text-sm md:block">
                <span className="block font-semibold">{user?.name ?? "Finance user"}</span>
                <span className="block text-xs text-slate-500">{role ? roleLabels[role] : "Role"}</span>
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {user?.isPlatformOwner ? <DropdownMenuItem onSelect={() => navigate("/super-admin/dashboard")}>Super Admin platform</DropdownMenuItem> : null}
            {user && user.roles.filter((item) => item !== "spectra_super_admin").length > 1 ? user.roles.filter((item) => item !== "spectra_super_admin").map((item) => <DropdownMenuItem key={item} onSelect={() => { setActiveRole(item); navigate(`/app/dashboard/${dashboardRolePaths[item] ?? "read-only"}`); }}>Switch dashboard: {roleLabels[item]}</DropdownMenuItem>) : null}
            <DropdownMenuItem onSelect={() => navigate("/app/settings/company")}>Company profile</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => navigate("/app/audit")}>Audit activity</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => { logout(); navigate("/auth/login"); }}><LogOut className="mr-2 h-4 w-4" />Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
