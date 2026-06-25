import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

function toLabel(part: string): string {
  return part
    .replaceAll("-", " ")
    .replaceAll(/\b\w/g, (c) => c.toUpperCase());
}

export function Breadcrumbs() {
  const location = useLocation();
  const parts = location.pathname.split("/").filter(Boolean);
  const isSuperAdmin = parts[0] === "super-admin";
  const rootPath = isSuperAdmin ? "/super-admin/dashboard" : "/app/dashboard";
  const rootLabel = isSuperAdmin ? "Platform" : "Home";
  let path = isSuperAdmin ? "/super-admin" : "/app";
  return (
    <nav aria-label="Breadcrumbs" className="flex items-center gap-1 text-xs text-slate-500">
      <Link to={rootPath} className="inline-flex items-center gap-1 hover:text-primary"><Home className="h-3.5 w-3.5" />{rootLabel}</Link>
      {parts.slice(1).map((part) => {
        path += `/${part}`;
        return (
          <span key={path} className="inline-flex items-center gap-1">
            <ChevronRight className="h-3.5 w-3.5" />
            <span>{toLabel(part)}</span>
          </span>
        );
      })}
    </nav>
  );
}
