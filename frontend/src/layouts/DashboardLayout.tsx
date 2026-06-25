import { Outlet } from "react-router-dom";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { Topbar } from "@/components/layout/Topbar";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/utils/cn";

export function DashboardLayout() {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-navy-950">
      <AppSidebar />
      <div className={cn("min-h-screen transition-all duration-200 lg:pl-[240px]", collapsed && "lg:pl-[72px]")}> 
        <Topbar />
        <main className="min-w-0 px-4 py-6 md:px-6"><Outlet /></main>
      </div>
    </div>
  );
}
