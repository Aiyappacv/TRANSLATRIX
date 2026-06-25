import type * as React from "react";
import { SlidersHorizontal } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function FilterBar({ children }: { children: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><SlidersHorizontal className="h-4 w-4 text-primary" />Filters</div>
        <div className="grid gap-3 md:grid-cols-4">{children}</div>
      </CardContent>
    </Card>
  );
}
