import { CheckCircle2, Circle } from "lucide-react";
import { cn } from "@/utils/cn";

export function ProgressStepper({ steps, currentIndex }: { steps: string[]; currentIndex: number }) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step} className={cn("flex items-center gap-3 rounded-xl border p-3", index === currentIndex ? "border-primary bg-indigo-50 dark:bg-indigo-950/20" : "border-slate-200 dark:border-slate-800")}>
          {index < currentIndex ? <CheckCircle2 className="h-5 w-5 text-success" /> : <Circle className="h-5 w-5 text-slate-400" />}
          <span className="text-sm font-medium">{step}</span>
        </div>
      ))}
    </div>
  );
}
