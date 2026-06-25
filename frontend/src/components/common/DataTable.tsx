import { useMemo, useState } from "react";
import { ColumnDef, flexRender, getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import { Download, Search, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/utils/cn";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchPlaceholder?: string;
  dense?: boolean;
  exportFileName?: string;
}

function csvCell(value: unknown) {
  const text = value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export function DataTable<TData, TValue>({ columns, data, searchPlaceholder = "Search records...", dense = false, exportFileName = "translatrix-export" }: DataTableProps<TData, TValue>) {
  const [globalFilter, setGlobalFilter] = useState("");
  const memoColumns = useMemo(() => columns, [columns]);
  const table = useReactTable({
    data,
    columns: memoColumns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 8 } },
  });

  const exportCsv = () => {
    const visibleColumns = table.getAllLeafColumns().filter((column) => column.getIsVisible() && column.id !== "actions" && column.id !== "select");
    const headers = visibleColumns.map((column) => typeof column.columnDef.header === "string" ? column.columnDef.header : column.id);
    const rows = table.getFilteredRowModel().rows.map((row) => visibleColumns.map((column) => row.getValue(column.id)));
    const csv = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${exportFileName}-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input className="pl-9" placeholder={searchPlaceholder} value={globalFilter} onChange={(event) => setGlobalFilter(event.target.value)} />
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="outline" size="sm" aria-label="Toggle column visibility"><SlidersHorizontal className="h-4 w-4" />Columns</Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Visible columns</p>
              <div className="max-h-72 space-y-2 overflow-y-auto">
                {table.getAllLeafColumns().filter((column) => column.getCanHide()).map((column) => (
                  <Checkbox key={column.id} label={typeof column.columnDef.header === "string" ? column.columnDef.header : column.id} checked={column.getIsVisible()} onChange={(event) => column.toggleVisibility(event.target.checked)} />
                ))}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={!table.getFilteredRowModel().rows.length} aria-label="Export to CSV"><Download className="h-4 w-4" />Export</Button>
        </div>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" role="table">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900 dark:text-slate-400">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className={cn("whitespace-nowrap border-b border-slate-200 px-4 py-3 font-semibold dark:border-slate-800", dense && "px-3 py-2")}>{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows?.length ? table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/80 dark:border-slate-800 dark:hover:bg-slate-900/60">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className={cn("whitespace-nowrap px-4 py-3 align-middle", dense && "px-3 py-2")}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              )) : (
                <tr><td className="h-28 text-center text-slate-500" colSpan={table.getVisibleLeafColumns().length}>No matching records.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="flex flex-col items-center justify-between gap-2 text-sm text-slate-500 sm:flex-row">
        <span>{table.getFilteredRowModel().rows.length} records</span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()} aria-label="Previous page">Previous</Button>
          <span className="tabular">Page {table.getState().pagination.pageIndex + 1} / {table.getPageCount() || 1}</span>
          <Button variant="outline" size="sm" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()} aria-label="Next page">Next</Button>
        </div>
      </div>
    </div>
  );
}
