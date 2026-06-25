import { Activity, Clock3, Gauge, RadioTower } from "lucide-react";
import type { ProviderMonitor } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PlatformStatusBadge } from "./PlatformStatusBadge";
import { formatNumber } from "@/utils/formatters";

export function ProviderStatusCard({ provider }: { provider: ProviderMonitor }) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{provider.category}</p>
            <CardTitle className="mt-1 text-base">{provider.name}</CardTitle>
          </div>
          <PlatformStatusBadge status={provider.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><Gauge className="mb-2 h-4 w-4 text-primary" /><p className="text-xs text-slate-500">Success rate</p><p className="font-bold tabular">{provider.successRate == null ? "—" : `${provider.successRate}%`}</p></div>
          <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><Clock3 className="mb-2 h-4 w-4 text-primary" /><p className="text-xs text-slate-500">Latency</p><p className="font-bold tabular">{provider.latencyMs == null ? "—" : `${provider.latencyMs} ms`}</p></div>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500"><span className="inline-flex items-center gap-1"><RadioTower className="h-3.5 w-3.5" />Requests (24h)</span><span className="font-semibold text-slate-800 dark:text-slate-200">{formatNumber(provider.requests24h)}</span></div>
        <div className="flex items-center justify-between text-xs text-slate-500"><span className="inline-flex items-center gap-1"><Activity className="h-3.5 w-3.5" />Uptime</span><span className="font-semibold text-slate-800 dark:text-slate-200">{provider.uptimePercent == null ? "—" : `${provider.uptimePercent}%`}</span></div>
        {provider.message ? <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">{provider.message}</p> : null}
      </CardContent>
    </Card>
  );
}
