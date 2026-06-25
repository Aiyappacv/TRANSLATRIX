import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/utils/cn";

export function LoadingState({ label = "Loading secure workspace...", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("space-y-6", className)} role="status" aria-live="polite" aria-label={label}>
      <div className="space-y-2"><Skeleton className="h-4 w-40" /><Skeleton className="h-9 w-72 max-w-full" /><Skeleton className="h-4 w-full max-w-2xl" /></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-2xl" />)}</div>
      <Skeleton className="h-72 rounded-2xl" />
      <span className="sr-only">{label}</span>
    </div>
  );
}
