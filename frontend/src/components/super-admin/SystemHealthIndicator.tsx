import { Activity } from "lucide-react";
import { cn } from "@/utils/cn";

export function SystemHealthIndicator({ degraded = false }: { degraded?: boolean }) {
  return (
    <div className={cn(
      "hidden items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold md:flex",
      degraded
        ? "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
        : "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
    )}>
      <span className={cn("h-2 w-2 rounded-full", degraded ? "bg-amber-500" : "bg-emerald-500")} />
      <Activity className="h-3.5 w-3.5" />
      {degraded ? "Degraded service" : "All systems operational"}
    </div>
  );
}
