import type { ErrorCenterRecord } from "@/types";
import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RetryActionButton } from "./RetryActionButton";
import { ErrorDetailDrawer } from "./ErrorDetailDrawer";
import { formatDateTime } from "@/utils/formatters";

export function ErrorGroupCard({ title, errors, pendingId, onRetry }: { title: string; errors: ErrorCenterRecord[]; pendingId?: string; onRetry: (id: string) => void }) {
  return <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600" />{title}</CardTitle><CardDescription>{errors.length} error{errors.length === 1 ? "" : "s"} grouped by operational stage.</CardDescription></CardHeader><CardContent className="space-y-3">{errors.map((error) => <div key={error.id} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"><div><div className="flex flex-wrap items-center gap-2"><p className="font-semibold">{error.code}</p><Badge variant={error.severity === "critical" || error.severity === "high" ? "danger" : error.severity === "medium" ? "warning" : "neutral"}>{error.severity}</Badge><Badge variant={error.retryable ? "info" : "neutral"}>{error.retryable ? "Retryable" : "Non-retryable"}</Badge></div><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{error.message}</p><p className="mt-2 text-xs text-slate-500">{error.entityType} {error.entityId} · {formatDateTime(error.occurredAt)} · Request {error.requestId}</p></div><div className="flex gap-2"><ErrorDetailDrawer title={`${error.code} details`} details={JSON.stringify(error.details, null, 2)} /><RetryActionButton retryable={error.retryable} pending={pendingId === error.id} onRetry={() => onRetry(error.id)} /></div></div></div>)}</CardContent></Card>;
}
