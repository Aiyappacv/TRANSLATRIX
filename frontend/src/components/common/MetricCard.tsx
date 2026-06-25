import { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MetricCardProps {
  label: string;
  value: string;
  delta?: string;
  tone?: "success" | "warning" | "danger" | "info" | "neutral";
  icon?: LucideIcon;
}

export function MetricCard({ label, value, delta, tone = "neutral", icon: Icon }: MetricCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="truncate text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
            <p className="mt-1 whitespace-nowrap text-2xl font-bold tabular text-slate-900 dark:text-slate-50">{value}</p>
          </div>
          {Icon ? <div className="rounded-xl bg-indigo-50 p-2.5 text-primary dark:bg-indigo-950/40"><Icon className="h-5 w-5" /></div> : null}
        </div>
        {delta ? <Badge variant={tone} className="mt-4">{delta}</Badge> : null}
      </CardContent>
    </Card>
  );
}
