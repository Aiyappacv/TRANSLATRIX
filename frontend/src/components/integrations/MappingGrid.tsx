import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";

export interface MappingGridColumn<T> {
  key: keyof T;
  label: string;
  type?: "text" | "number" | "boolean";
  placeholder?: string;
}

export function MappingGrid<T extends { id: string }>({
  rows,
  columns,
  onChange,
  onAdd,
  emptyMessage = "No mappings configured.",
}: {
  rows: T[];
  columns: MappingGridColumn<T>[];
  onChange: (rows: T[]) => void;
  onAdd: () => T;
  emptyMessage?: string;
}) {
  const update = (index: number, key: keyof T, value: unknown) => {
    onChange(rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  };

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[780px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900">
            <tr>
              {columns.map((column) => <th key={String(column.key)} className="border-b border-slate-200 px-3 py-3 font-semibold dark:border-slate-800">{column.label}</th>)}
              <th className="w-14 border-b border-slate-200 px-3 py-3 dark:border-slate-800" />
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row, index) => (
              <tr key={row.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                {columns.map((column) => (
                  <td key={String(column.key)} className="px-3 py-2 align-middle">
                    {column.type === "boolean" ? (
                      <Switch checked={Boolean(row[column.key])} onChange={(event) => update(index, column.key, event.target.checked)} />
                    ) : (
                      <Input
                        type={column.type === "number" ? "number" : "text"}
                        value={String(row[column.key] ?? "")}
                        placeholder={column.placeholder}
                        onChange={(event) => update(index, column.key, column.type === "number" ? Number(event.target.value) : event.target.value)}
                      />
                    )}
                  </td>
                ))}
                <td className="px-3 py-2"><Button type="button" variant="ghost" size="icon" aria-label="Delete mapping" onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2 className="h-4 w-4" /></Button></td>
              </tr>
            )) : <tr><td colSpan={columns.length + 1} className="h-24 text-center text-slate-500">{emptyMessage}</td></tr>}
          </tbody>
        </table>
      </div>
      <Button type="button" variant="outline" onClick={() => onChange([...rows, onAdd()])}><Plus className="h-4 w-4" />Add mapping</Button>
    </div>
  );
}
