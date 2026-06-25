import type { ReactNode } from "react";
import { FileSearch } from "lucide-react";

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-950">
      <div className="rounded-2xl bg-indigo-50 p-4 text-primary dark:bg-indigo-950/50"><FileSearch className="h-8 w-8" /></div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      {description ? <p className="mt-2 max-w-md text-sm text-slate-500">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
