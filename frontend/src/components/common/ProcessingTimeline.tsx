import { AlertTriangle, CheckCircle2, Circle, Clock3, Loader2 } from "lucide-react";
import type { BatchTimelineStep } from "@/types";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/utils/formatters";
import { cn } from "@/utils/cn";

const iconMap = {
  completed: CheckCircle2,
  processing: Loader2,
  pending: Clock3,
  failed: AlertTriangle,
  warning: AlertTriangle,
};

const toneMap = {
  completed: "text-success bg-success/10 border-success/20",
  processing: "text-primary bg-primary/10 border-primary/20",
  pending: "text-slate-400 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-800",
  failed: "text-danger bg-danger/10 border-danger/20",
  warning: "text-warning bg-warning/10 border-warning/20",
};

export function ProcessingTimeline({ steps }: { steps: BatchTimelineStep[] }) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const Icon = iconMap[step.status] ?? Circle;
        return (
          <div key={step.id} className="relative flex gap-4">
            {index < steps.length - 1 ? <div className="absolute left-5 top-11 h-[calc(100%-1.25rem)] w-px bg-slate-200 dark:bg-slate-800" /> : null}
            <div className={cn("z-10 flex h-10 w-10 items-center justify-center rounded-full border", toneMap[step.status])}>
              <Icon className={cn("h-5 w-5", step.status === "processing" && "animate-spin")} />
            </div>
            <div className="flex-1 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="font-semibold text-slate-900 dark:text-slate-50">{step.label}</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
                </div>
                <Badge variant={step.status === "failed" ? "danger" : step.status === "completed" ? "success" : step.status === "processing" ? "info" : step.status === "warning" ? "warning" : "neutral"}>
                  {step.status.replace("_", " ")}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                {step.timestamp ? <span>{formatDateTime(step.timestamp)}</span> : <span>Waiting for previous step</span>}
                {step.actor ? <span>Actor: {step.actor}</span> : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
