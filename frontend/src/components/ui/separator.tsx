import type * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { cn } from "@/utils/cn";

export function Separator({ className, orientation = "horizontal", ...props }: React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>) {
  return <SeparatorPrimitive.Root orientation={orientation} className={cn("shrink-0 bg-slate-200 dark:bg-slate-800", orientation === "horizontal" ? "h-px w-full" : "h-full w-px", className)} {...props} />;
}
