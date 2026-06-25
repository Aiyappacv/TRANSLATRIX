import { cn } from "@/utils/cn";

export function Avatar({ name, src, className }: { name: string; src?: string; className?: string }) {
  const initials = name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  return src ? (
    <img src={src} alt={name} className={cn("h-9 w-9 rounded-full object-cover", className)} />
  ) : (
    <span className={cn("inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-gradient text-xs font-bold text-white", className)}>{initials}</span>
  );
}
