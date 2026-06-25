import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock3, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import type { FileProcessingLog, WorkerStatus } from "@/types";
import { fileApi } from "@/services/fileApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/utils/formatters";
import { cn } from "@/utils/cn";
import { usePermissions } from "@/hooks/usePermissions";
import { permissions } from "@/utils/permissions";

const iconMap: Record<WorkerStatus, typeof CheckCircle2> = {
  completed: CheckCircle2,
  processing: Loader2,
  queued: Clock3,
  failed: AlertTriangle,
  retrying: RefreshCw,
};

export function ProcessingLogsPanel({ fileId, logs }: { fileId: string; logs: FileProcessingLog[] }) {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const canProcess = hasPermission(permissions.filesProcess);
  const retry = useMutation({
    mutationFn: (step: string) => fileApi.retryProcessingStep(fileId, step),
    onSuccess: async (result) => {
      toast.success(`${result.step} queued for retry`);
      await queryClient.invalidateQueries({ queryKey: ["file", fileId] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to retry processing step"),
  });

  if (!logs.length) {
    return <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">No processing logs yet.</div>;
  }

  return (
    <div className="space-y-3">
      {logs.map((log, index) => {
        const Icon = iconMap[log.status];
        const retryingThis = retry.isPending && retry.variables === log.step;
        return (
          <div key={log.id} className="relative flex gap-4">
            {index < logs.length - 1 ? <div className="absolute left-5 top-11 h-[calc(100%-1.25rem)] w-px bg-slate-200 dark:bg-slate-800" /> : null}
            <div className={cn("z-10 flex h-10 w-10 items-center justify-center rounded-full border",
              log.status === "completed" && "border-success/20 bg-success/10 text-success",
              log.status === "failed" && "border-danger/20 bg-danger/10 text-danger",
              log.status === "processing" && "border-primary/20 bg-primary/10 text-primary",
              (log.status === "queued" || log.status === "retrying") && "border-warning/20 bg-warning/10 text-warning",
            )}>
              <Icon className={cn("h-5 w-5", (log.status === "processing" || log.status === "retrying") && "animate-spin")} />
            </div>
            <div className="flex-1 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="font-semibold">{log.step}</p>
                  <p className="mt-1 text-sm text-slate-500">{log.message}</p>
                  {log.errorDetails ? <p className="mt-2 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">{log.errorDetails}</p> : null}
                  <p className="mt-2 text-xs text-slate-500">Worker: {log.worker} · Started {formatDateTime(log.startedAt)}{log.completedAt ? ` · Completed ${formatDateTime(log.completedAt)}` : ""}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={log.status === "completed" ? "success" : log.status === "failed" ? "danger" : log.status === "processing" ? "info" : "warning"}>{log.status}</Badge>
                  {log.retryable && canProcess ? (
                    <Button variant="outline" size="sm" disabled={retry.isPending} onClick={() => retry.mutate(log.step)}>
                      <RefreshCw className={cn("h-4 w-4", retryingThis && "animate-spin")} />{retryingThis ? "Retrying..." : "Retry failed step"}
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
