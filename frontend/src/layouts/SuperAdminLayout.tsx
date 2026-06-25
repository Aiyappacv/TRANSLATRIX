import { Outlet, useLocation } from "react-router-dom";
import { SuperAdminSidebar } from "@/components/super-admin/SuperAdminSidebar";
import { SuperAdminTopbar } from "@/components/super-admin/SuperAdminTopbar";
import { TenantAuditBanner } from "@/components/super-admin/TenantAuditBanner";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";

export function SuperAdminLayout() {
  const location = useLocation();
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const viewingTenant = /^\/super-admin\/companies\/[^/]+/.test(location.pathname);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-navy-950">
      <SuperAdminSidebar />
      <div className={cn("min-h-screen transition-all duration-200 lg:pl-[240px]", collapsed && "lg:pl-[72px]")}>
        <SuperAdminTopbar />
        <main className="min-w-0 px-4 py-6 md:px-6">
          {viewingTenant ? <TenantAuditBanner /> : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
