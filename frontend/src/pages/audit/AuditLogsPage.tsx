import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download } from "lucide-react";
import type { AuditLogRecord } from "@/types";
import { monitoringApi } from "@/services/monitoringApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { DataTable } from "@/components/common/DataTable";
import { JsonDiffViewer } from "@/components/common/JsonDiffViewer";
import { FilterBar } from "@/components/common/FilterBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { formatDateTime } from "@/utils/formatters";
import { downloadCsv } from "@/utils/downloads";

export function AuditLogsPage() {
  const query = useQuery({ queryKey: ["monitoring", "audit-logs"], queryFn: monitoringApi.getAuditLogs });
  const [filters, setFilters] = useState({ user: "", action: "", entityType: "", entityId: "" });
  const filtered = useMemo(() => (query.data ?? []).filter((row) => (!filters.user || row.user.toLowerCase().includes(filters.user.toLowerCase())) && (!filters.action || row.action.toLowerCase().includes(filters.action.toLowerCase())) && (!filters.entityType || row.entityType.toLowerCase().includes(filters.entityType.toLowerCase())) && (!filters.entityId || [row.entityId, row.batchId, row.entryId, row.sapPostingId].filter(Boolean).some((value) => value!.toLowerCase().includes(filters.entityId.toLowerCase())))), [filters, query.data]);
  const columns: ColumnDef<AuditLogRecord>[] = [
    { accessorKey: "timestamp", header: "Timestamp", cell: ({ row }) => formatDateTime(row.original.timestamp) },
    { accessorKey: "user", header: "User" }, { accessorKey: "action", header: "Action", cell: ({ row }) => <Badge variant="info">{row.original.action}</Badge> },
    { accessorKey: "entityType", header: "Entity type" }, { accessorKey: "entityId", header: "Entity ID" },
    { accessorKey: "ipAddress", header: "IP address" }, { accessorKey: "requestId", header: "Request ID" },
    { id: "detail", header: "Detail", cell: ({ row }) => <Dialog><DialogTrigger asChild><Button size="sm" variant="outline">Inspect</Button></DialogTrigger><DialogContent className="max-w-4xl"><DialogHeader><DialogTitle>{row.original.action}</DialogTitle><DialogDescription>{row.original.user} · {formatDateTime(row.original.timestamp)} · {row.original.requestId}</DialogDescription></DialogHeader><JsonDiffViewer oldValue={row.original.oldValue} newValue={row.original.newValue} /><pre className="max-h-52 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(row.original.metadata, null, 2)}</pre></DialogContent></Dialog> },
  ];
  const exportAudit = () => downloadCsv(
    `translatrix-audit-${new Date().toISOString().slice(0, 10)}.csv`,
    ["Timestamp", "User", "Action", "Entity type", "Entity ID", "Old value", "New value", "IP address", "Request ID", "Batch ID", "Entry ID", "SAP posting ID"],
    filtered.map((row) => [row.timestamp, row.user, row.action, row.entityType, row.entityId, row.oldValue, row.newValue, row.ipAddress, row.requestId, row.batchId, row.entryId, row.sapPostingId]),
  );
  return <div className="space-y-6"><PageHeader eyebrow="Phase 13 · Monitoring" title="Audit logs" description="Timestamp, user, action, entity, old/new values, IP address, request ID, and immutable metadata." actions={<Button variant="outline" onClick={exportAudit} disabled={!filtered.length}><Download className="h-4 w-4" />Export audit CSV</Button>} />
    <FilterBar><Input placeholder="User" value={filters.user} onChange={(event) => setFilters((value) => ({ ...value, user: event.target.value }))} /><Input placeholder="Action" value={filters.action} onChange={(event) => setFilters((value) => ({ ...value, action: event.target.value }))} /><Input placeholder="Entity type" value={filters.entityType} onChange={(event) => setFilters((value) => ({ ...value, entityType: event.target.value }))} /><Input placeholder="Batch, entry, posting, or entity ID" value={filters.entityId} onChange={(event) => setFilters((value) => ({ ...value, entityId: event.target.value }))} /></FilterBar>
    {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState title="Audit logs unavailable" description="Audit events could not be loaded." onRetry={() => query.refetch()} /> : <DataTable columns={columns} data={filtered} searchPlaceholder="Search audit events..." exportFileName="audit-logs" />}
  </div>;
}
