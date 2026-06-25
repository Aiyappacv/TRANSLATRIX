import type * as React from "react";

export function Tooltip({ children, content }: { children: React.ReactNode; content: React.ReactNode }) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden w-max max-w-xs -translate-x-1/2 rounded-lg bg-slate-950 px-2 py-1 text-xs text-white shadow-lg group-hover:block">
        {content}
      </span>
    </span>
  );
}
