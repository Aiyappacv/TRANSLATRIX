import { CheckCircle2, Clock3 } from "lucide-react";

export function Timeline({ items }: { items: Array<{ title: string; description?: string; done?: boolean }> }) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="flex gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
          {item.done ? <CheckCircle2 className="h-5 w-5 text-success" /> : <Clock3 className="h-5 w-5 text-warning" />}
          <div><p className="font-medium">{item.title}</p>{item.description ? <p className="text-sm text-slate-500">{item.description}</p> : null}</div>
        </div>
      ))}
    </div>
  );
}
