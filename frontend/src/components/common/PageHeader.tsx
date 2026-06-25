import { useEffect, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { APP_NAME } from "@/utils/constants";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  badge?: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, badge, actions }: PageHeaderProps) {
  useEffect(() => { document.title = `${title} · ${APP_NAME}`; }, [title]);
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">{eyebrow}</p> : null}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 md:text-3xl">{title}</h1>
          {badge ? <Badge variant="brand">{badge}</Badge> : null}
        </div>
        {description ? <p className="mt-1 max-w-3xl truncate text-sm text-slate-500 dark:text-slate-400">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  );
}
