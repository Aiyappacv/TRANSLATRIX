import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Search } from "lucide-react";
import { navGroups } from "@/app/routeConfig";
import { usePermissions } from "@/hooks/usePermissions";
import { Input } from "@/components/ui/input";

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { hasAnyPermission } = usePermissions();

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return [];
    return navGroups.flatMap((group) => group.items
      .filter((item) => hasAnyPermission(item.permissions))
      .filter((item) => `${group.label} ${item.label}`.toLowerCase().includes(normalized))
      .map((item) => ({ ...item, group: group.label })))
      .slice(0, 8);
  }, [hasAnyPermission, query]);

  useEffect(() => {
    setOpen(false);
    setQuery("");
  }, [location.pathname, location.search]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  return (
    <div ref={wrapperRef} className="relative w-44 lg:w-56">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <Input
        aria-label="Global navigation search"
        placeholder="Search pages..."
        className="pl-9 h-9 text-xs"
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(event) => { setQuery(event.target.value); setOpen(true); }}
      />
      {open && query.trim() ? (
        <div className="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-enterprise dark:border-slate-800 dark:bg-slate-950">
          {results.length ? results.map((result) => (
            <Link key={`${result.group}-${result.path}`} to={result.path} className="block border-b border-slate-100 px-4 py-3 last:border-b-0 hover:bg-slate-50 dark:border-slate-900 dark:hover:bg-slate-900">
              <p className="text-sm font-semibold">{result.label}</p>
              <p className="text-xs text-slate-500">{result.group}</p>
            </Link>
          )) : <p className="px-4 py-6 text-center text-sm text-slate-500">No accessible pages match “{query}”.</p>}
        </div>
      ) : null}
    </div>
  );
}
