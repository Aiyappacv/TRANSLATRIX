function stringify(value: unknown) {
  return value == null ? "—" : JSON.stringify(value, null, 2);
}

export function JsonDiffViewer({ oldValue, newValue }: { oldValue?: unknown; newValue?: unknown }) {
  return <div className="grid gap-4 md:grid-cols-2"><div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Old value</p><pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{stringify(oldValue)}</pre></div><div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">New value</p><pre className="max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{stringify(newValue)}</pre></div></div>;
}
