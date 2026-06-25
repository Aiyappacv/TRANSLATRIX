import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ScrollText, ShieldCheck, ShieldX } from "lucide-react";
import type { PlatformAuditRecord } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { DataTable } from "@/components/common/DataTable";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { useToast } from "@/hooks/useToast";
import { downloadJson } from "@/utils/downloads";
import { formatDateTime } from "@/utils/formatters";

const columns: ColumnDef<PlatformAuditRecord>[] = [
  { accessorKey: "createdAt", header: "Timestamp", cell: ({ row }) => formatDateTime(row.original.createdAt) },
  { accessorKey: "actor", header: "Actor" },
  { accessorKey: "action", header: "Action" },
  { accessorKey: "targetName", header: "Target", cell: ({ row }) => <div><p className="font-semibold">{row.original.targetName}</p><p className="text-xs text-slate-500">{row.original.targetType}</p></div> },
  { accessorKey: "companyName", header: "Tenant", cell: ({ row }) => row.original.companyName ?? "Platform" },
  { accessorKey: "ipAddress", header: "IP address" },
  { accessorKey: "result", header: "Result", cell: ({ row }) => <PlatformStatusBadge status={row.original.result} /> },
  { accessorKey: "details", header: "Details", cell: ({ row }) => <p className="max-w-sm text-xs leading-5 text-slate-500">{row.original.details}</p> },
];

export function SuperAdminAuditLogsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const logs = useQuery({ queryKey: ["super-admin", "audit"], queryFn: superAdminApi.getAuditLogs });
  const exportLog = useMutation({
    mutationFn: superAdminApi.getSignedAuditExport,
    onSuccess: async (payload) => {
      downloadJson(`translatrix-platform-audit-${payload.generatedAt.slice(0, 10)}.signed.json`, payload);
      await queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] });
      toast.success("Signed audit export created", `${payload.records.length} records · ${payload.signature}`);
    },
    onError: (error) => toast.error("Audit export failed", error instanceof Error ? error.message : "Unable to export audit records."),
  });
  if (logs.isLoading) return <LoadingState label="Loading platform audit logs..." />;
  const data = logs.data ?? [];
  return (
    <>
      <PageHeader eyebrow="Platform governance" title="Super Admin audit logs" description="Immutable records for tenant views, configuration changes, support access, exports, integration tests, and denied platform actions." actions={<Button variant="outline" disabled={exportLog.isPending} onClick={() => exportLog.mutate()}><Download className="h-4 w-4" />{exportLog.isPending ? "Signing..." : "Export signed log"}</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-3"><MetricCard label="Recorded events" value={String(data.length)} icon={ScrollText} /><MetricCard label="Successful" value={String(data.filter((item) => item.result === "success").length)} tone="success" icon={ShieldCheck} /><MetricCard label="Denied or failed" value={String(data.filter((item) => item.result !== "success").length)} tone="danger" icon={ShieldX} /></div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search actors, actions, tenants, targets, IPs..." exportFileName="platform-audit-logs" /></CardContent></Card>
    </>
  );
}
