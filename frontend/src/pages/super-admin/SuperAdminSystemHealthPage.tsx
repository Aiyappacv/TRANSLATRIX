import { useQuery } from "@tanstack/react-query";
import { Activity, Cpu, Database, MemoryStick } from "lucide-react";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { Progress } from "@/components/ui/progress";
import { formatDateTime } from "@/utils/formatters";

export function SuperAdminSystemHealthPage() {
  const health = useQuery({ queryKey: ["super-admin", "system-health"], queryFn: superAdminApi.getSystemHealth });
  if (health.isLoading) return <LoadingState label="Loading system health..." />;
  const data = health.data ?? [];
  const avgLatency = Math.round(data.reduce((sum, service) => sum + service.latencyMs, 0) / Math.max(data.length, 1));
  return (
    <>
      <PageHeader eyebrow="Platform reliability" title="System health" description="Observe service availability, latency, resource utilization, deployment recency, and platform SLO posture." />
      <div className="mb-6 grid gap-4 md:grid-cols-4"><MetricCard label="Services" value={String(data.length)} icon={Database} /><MetricCard label="Operational" value={String(data.filter((service) => service.status === "operational").length)} tone="success" icon={Activity} /><MetricCard label="Average latency" value={`${avgLatency} ms`} tone="info" icon={Cpu} /><MetricCard label="Degraded" value={String(data.filter((service) => service.status === "degraded").length)} tone="warning" icon={MemoryStick} /></div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {data.map((service) => (
          <Card key={service.id}>
            <CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle className="text-base">{service.name}</CardTitle><CardDescription>{service.region}</CardDescription></div><PlatformStatusBadge status={service.status} /></div></CardHeader>
            <CardContent className="space-y-4">
              <div><div className="mb-1 flex justify-between text-xs"><span>CPU</span><span>{service.cpuPercent}%</span></div><Progress value={service.cpuPercent} /></div>
              <div><div className="mb-1 flex justify-between text-xs"><span>Memory</span><span>{service.memoryPercent}%</span></div><Progress value={service.memoryPercent} /></div>
              <div className="grid grid-cols-2 gap-3 text-sm"><div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">Uptime</p><p className="mt-1 font-bold">{service.uptimePercent}%</p></div><div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">Latency</p><p className="mt-1 font-bold">{service.latencyMs} ms</p></div></div>
              {service.message ? <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">{service.message}</p> : null}
              <p className="text-xs text-slate-500">Last check/deployment: {formatDateTime(service.lastDeploymentAt)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
