import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({ title = "Something went wrong", description, onRetry }: { title?: string; description?: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5" />
        <div>
          <h3 className="font-semibold">{title}</h3>
          {description ? <p className="mt-1 text-sm opacity-80">{description}</p> : null}
          {onRetry ? <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>Retry</Button> : null}
        </div>
      </div>
    </div>
  );
}
