import type { IntegrationProvider } from "@/types";
import { cn } from "@/utils/cn";

export function IntegrationLogo({ provider, className }: { provider: IntegrationProvider; className?: string }) {
  return (
    <div className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-indigo-100 bg-indigo-50 text-sm font-black tracking-tight text-indigo-700 dark:border-indigo-900/60 dark:bg-indigo-950/40 dark:text-indigo-300", className)} aria-label={`${provider.name} logo placeholder`}>
      {provider.logoText ?? provider.shortName?.slice(0, 3).toUpperCase() ?? provider.name.slice(0, 2).toUpperCase()}
    </div>
  );
}
