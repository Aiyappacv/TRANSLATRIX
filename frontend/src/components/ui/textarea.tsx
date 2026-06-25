import * as React from "react";
import { cn } from "@/utils/cn";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    className={cn("min-h-24 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus-ring dark:border-slate-800 dark:bg-slate-950", className)}
    ref={ref}
    {...props}
  />
));
Textarea.displayName = "Textarea";
