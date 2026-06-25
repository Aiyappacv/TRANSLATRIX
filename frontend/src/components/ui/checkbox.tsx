import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/utils/cn";

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(({ className, label, ...props }, ref) => (
  <label className="inline-flex items-center gap-2 text-sm">
    <span className="relative inline-flex h-5 w-5 items-center justify-center">
      <input ref={ref} type="checkbox" className={cn("peer h-5 w-5 appearance-none rounded-md border border-slate-300 bg-white checked:border-primary checked:bg-primary focus-ring dark:border-slate-700 dark:bg-slate-950", className)} {...props} />
      <Check className="pointer-events-none absolute h-3.5 w-3.5 text-white opacity-0 peer-checked:opacity-100" />
    </span>
    {label ? <span>{label}</span> : null}
  </label>
));
Checkbox.displayName = "Checkbox";
