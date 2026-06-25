import * as React from "react";
import { cn } from "@/utils/cn";

export interface SwitchProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  checked?: boolean;
  defaultChecked?: boolean;
  label?: string;
  name?: string;
  value?: string;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onCheckedChange?: (checked: boolean) => void;
}

export const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(({
  className,
  checked,
  defaultChecked = false,
  disabled,
  label,
  name,
  value,
  onChange,
  onCheckedChange,
  onClick,
  ...props
}, ref) => {
  const controlled = checked !== undefined;
  const [internal, setInternal] = React.useState(defaultChecked);
  const active = controlled ? Boolean(checked) : internal;

  const update = (next: boolean) => {
    if (!controlled) setInternal(next);
    onCheckedChange?.(next);
    if (onChange) {
      onChange({ target: { checked: next, name, value } } as React.ChangeEvent<HTMLInputElement>);
    }
  };

  return (
    <label className={cn("inline-flex items-center gap-2 text-sm", disabled && "cursor-not-allowed opacity-60")}>
      <button
        {...props}
        ref={ref}
        type="button"
        role="switch"
        aria-checked={active}
        aria-label={props["aria-label"] ?? label}
        disabled={disabled}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
          active ? "bg-primary" : "bg-slate-300 dark:bg-slate-700",
          className,
        )}
        onClick={(event) => {
          onClick?.(event);
          if (!event.defaultPrevented && !disabled) update(!active);
        }}
      >
        <span className={cn("pointer-events-none block h-5 w-5 rounded-full bg-white shadow transition-transform", active ? "translate-x-5" : "translate-x-0.5")} />
      </button>
      {label ? <span>{label}</span> : null}
    </label>
  );
});
Switch.displayName = "Switch";
