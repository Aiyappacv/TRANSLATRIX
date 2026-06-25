import type { AuditEvent } from "@/types";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/utils/formatters";

const tone = { success: "success", warning: "warning", failed: "danger", info: "info" } as const;
export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="relative pl-7">
          <div className="absolute left-0 top-1.5 h-3 w-3 rounded-full bg-primary ring-4 ring-indigo-50 dark:ring-indigo-950" />
          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-900 dark:text-slate-50">{event.action}</p>
                <p className="mt-1 text-xs text-slate-500">{event.actor} · {formatDateTime(event.timestamp)} · {event.entityType}:{event.entityId}</p>
              </div>
              <Badge variant={tone[event.status]}>{event.status}</Badge>
            </div>
            {(event.oldValue || event.newValue) ? <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300">{event.oldValue ? `Old: ${event.oldValue} · ` : ""}{event.newValue ? `New: ${event.newValue}` : ""}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
