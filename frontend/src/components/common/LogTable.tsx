import type { ColumnDef } from "@tanstack/react-table";
import type { ProcessingLogRecord } from "@/types";
import { DataTable } from "./DataTable";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/utils/formatters";

const columns: ColumnDef<ProcessingLogRecord>[] = [
  { accessorKey: "timestamp", header: "Timestamp", cell: ({ row }) => formatDateTime(row.original.timestamp) },
  { accessorKey: "level", header: "Level", cell: ({ row }) => <Badge variant={row.original.level === "error" ? "danger" : row.original.level === "warning" ? "warning" : row.original.level === "success" ? "success" : "info"}>{row.original.level}</Badge> },
  { accessorKey: "stage", header: "Stage", cell: ({ row }) => <span className="font-semibold">{row.original.stage.replaceAll("_", " ")}</span> },
  { accessorKey: "jobId", header: "Job ID" },
  { accessorKey: "batchId", header: "Batch" },
  { accessorKey: "fileId", header: "File" },
  { accessorKey: "message", header: "Message", cell: ({ row }) => <p className="max-w-[420px]">{row.original.message}</p> },
  { accessorKey: "durationMs", header: "Duration", cell: ({ row }) => row.original.durationMs ? `${row.original.durationMs} ms` : "—" },
  { accessorKey: "retryCount", header: "Retries" },
  { accessorKey: "requestId", header: "Request ID" },
];

export function LogTable({ logs }: { logs: ProcessingLogRecord[] }) {
  return <DataTable columns={columns} data={logs} searchPlaceholder="Search jobs, stages, files, messages, and request IDs..." exportFileName="processing-logs" dense />;
}
