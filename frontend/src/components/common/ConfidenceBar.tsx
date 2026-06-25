import { Progress } from "@/components/ui/progress";
import { formatPercent } from "@/utils/formatters";
import { cn } from "@/utils/cn";

export function ConfidenceBar({ label, value, threshold = 0.9, compact = false }: { label: string; value: number; threshold?: number; compact?: boolean }) {
  const tone = value >= threshold ? "text-emerald-600" : value >= threshold - 0.1 ? "text-amber-600" : "text-red-600";
  return (
    <div className={cn("space-y-1", compact && "space-y-0.5")}>
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-medium text-slate-500 dark:text-slate-400">{label}</span>
        <span className={cn("font-semibold tabular", tone)}>{formatPercent(value)}</span>
      </div>
      <Progress value={value * 100} className={compact ? "h-1.5" : "h-2"} />
    </div>
  );
}
