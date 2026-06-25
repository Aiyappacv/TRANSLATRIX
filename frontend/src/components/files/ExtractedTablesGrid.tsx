import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Download, Edit3, Save, X } from "lucide-react";
import { toast } from "sonner";
import type { ExtractedTable } from "@/types";
import { fileApi } from "@/services/fileApi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { usePermissions } from "@/hooks/usePermissions";
import { permissions } from "@/utils/permissions";

function toRows(table: ExtractedTable) {
  return table.rows.map((row) => row.map((cell) => cell.correctedValue ?? cell.value));
}

function escapeCsv(value: string) {
  return /[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function downloadTable(table: ExtractedTable, rows: string[][], format: "json" | "csv") {
  const content = format === "json"
    ? JSON.stringify({ headers: table.headers, rows }, null, 2)
    : [table.headers.map(escapeCsv).join(","), ...rows.map((row) => row.map(escapeCsv).join(","))].join("\n");
  const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${table.name.replaceAll(" ", "_")}.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

interface TableCardProps {
  fileId: string;
  table: ExtractedTable;
}

function TableCard({ fileId, table }: TableCardProps) {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const canProcess = hasPermission(permissions.filesProcess);
  const sourceRows = useMemo(() => toRows(table), [table]);
  const [rows, setRows] = useState<string[][]>(sourceRows);
  const [editing, setEditing] = useState(false);

  useEffect(() => setRows(sourceRows), [sourceRows]);

  const save = useMutation({
    mutationFn: () => fileApi.saveTableCorrections(fileId, table.id, rows),
    onSuccess: async () => {
      toast.success(`${table.name} corrections saved`);
      setEditing(false);
      await queryClient.invalidateQueries({ queryKey: ["file", fileId] });
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save table corrections"),
  });

  const updateCell = (rowIndex: number, columnIndex: number, value: string) => {
    setRows((current) => current.map((row, r) => (
      r === rowIndex ? row.map((cell, c) => (c === columnIndex ? value : cell)) : row
    )));
  };

  const cancel = () => {
    setRows(sourceRows);
    setEditing(false);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold">{table.name}</p>
            <Badge variant="brand">Page {table.pageNumber}</Badge>
            {editing ? <Badge variant="warning">Correction mode</Badge> : null}
          </div>
          <div className="mt-2 w-64"><ConfidenceBar label="Table confidence" value={table.confidence} compact /></div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!editing ? (
            canProcess ? <Button variant="outline" size="sm" onClick={() => setEditing(true)}><Edit3 className="h-4 w-4" />Correct cells</Button> : null
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={cancel} disabled={save.isPending}><X className="h-4 w-4" />Cancel</Button>
              <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}><Save className="h-4 w-4" />{save.isPending ? "Saving..." : "Save corrections"}</Button>
            </>
          )}
          <Button variant="outline" size="sm" onClick={() => downloadTable(table, rows, "json")}><Download className="h-4 w-4" />Export JSON</Button>
          <Button variant="outline" size="sm" onClick={() => downloadTable(table, rows, "csv")}><Download className="h-4 w-4" />Export CSV</Button>
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900">
            <tr>
              {table.headers.map((header, index) => <th key={`${header}-${index}`} className="border-r border-slate-200 px-3 py-2 text-left last:border-r-0 dark:border-slate-800">{header}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-t border-slate-200 dark:border-slate-800">
                {row.map((cell, columnIndex) => {
                  const changed = rows[rowIndex]?.[columnIndex] !== cell.value;
                  return (
                    <td key={cell.id} className="border-r border-slate-200 px-3 py-2 align-top last:border-r-0 dark:border-slate-800">
                      <div className="flex min-w-36 flex-col gap-1">
                        {editing ? (
                          <Input
                            aria-label={`Correct ${table.headers[columnIndex] ?? `column ${columnIndex + 1}`}, row ${rowIndex + 1}`}
                            className="h-8 text-xs"
                            value={rows[rowIndex]?.[columnIndex] ?? ""}
                            onChange={(event) => updateCell(rowIndex, columnIndex, event.target.value)}
                          />
                        ) : (
                          <span className="text-sm">{rows[rowIndex]?.[columnIndex] ?? ""}</span>
                        )}
                        <span className="flex items-center gap-1 text-[11px] text-slate-500">
                          {changed ? <><Check className="h-3 w-3 text-success" />Corrected · </> : null}
                          {Math.round(cell.confidence * 100)}% confidence
                        </span>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ExtractedTablesGrid({ fileId, tables }: { fileId: string; tables: ExtractedTable[] }) {
  if (!tables.length) {
    return <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">No extracted tables found for this file.</div>;
  }

  return <div className="space-y-6">{tables.map((table) => <TableCard key={table.id} fileId={fileId} table={table} />)}</div>;
}
