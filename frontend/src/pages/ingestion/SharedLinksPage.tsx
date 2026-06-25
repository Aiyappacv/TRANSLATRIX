import { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, Link2, Plus, RefreshCcw } from "lucide-react";
import type { SharedLinkSource } from "@/types";
import { ingestionApi } from "@/services/ingestionApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";

const columns: ColumnDef<SharedLinkSource>[] = [
  {
    accessorKey: "name",
    header: "Source",
    cell: ({ row }) => (
      <div>
        <Link className="font-semibold text-primary hover:underline" to={`/app/ingestion/shared-links/${row.original.id}`}>{row.original.name}</Link>
        <p className="text-xs text-slate-500">{row.original.clientName}</p>
      </div>
    ),
  },
  { accessorKey: "sourceType", header: "Source type", cell: ({ row }) => <Badge variant="brand">{row.original.sourceType}</Badge> },
  { accessorKey: "authenticationType", header: "Auth" },
  { accessorKey: "schedule", header: "Schedule" },
  { accessorKey: "lastSyncAt", header: "Last sync", cell: ({ row }) => formatDateTime(row.original.lastSyncAt) },
  { accessorKey: "filesDiscovered", header: "Files found", cell: ({ row }) => <span className="font-semibold tabular">{row.original.filesDiscovered}</span> },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status === "failed" ? "sap_failed" : row.original.status === "active" ? "completed" : "draft"} /> },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => (
      <Button asChild size="sm" variant="outline">
        <Link to={`/app/ingestion/shared-links/${row.original.id}`}>Open</Link>
      </Button>
    ),
  },
];

export function SharedLinksPage() {
  const toast = useToast();
  const query = useQuery({ queryKey: ["shared-links"], queryFn: ingestionApi.getSharedLinks });
  const syncMutation = useMutation({ mutationFn: ingestionApi.syncAll, onSuccess: (result) => toast.success("Shared links synchronized", `Completed at ${new Date(result.syncedAt).toLocaleTimeString()}`), onError: (error) => toast.error("Synchronization failed", error instanceof Error ? error.message : "Unknown error") });
  const links = query.data ?? [];
  const active = links.filter((link) => link.status === "active").length;
  const files = links.reduce((sum, link) => sum + link.filesDiscovered, 0);
  const warnings = links.filter((link) => link.validation?.securityWarning).length;

  return (
    <>
      <PageHeader
        eyebrow="Ingestion"
        title="Shared link sources"
        description="Create, validate, schedule, disable, and monitor approved client file source links."
        actions={
          <>
            <Button variant="outline" disabled={syncMutation.isPending} onClick={() => syncMutation.mutate()}><RefreshCcw className={`h-4 w-4 ${syncMutation.isPending ? "animate-spin" : ""}`} />Sync all</Button>
            <Button asChild><Link to="/app/ingestion/shared-links/new"><Plus className="h-4 w-4" />Create shared link</Link></Button>
          </>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Active sources" value={String(active)} tone="success" icon={Link2} />
        <MetricCard label="Files discovered" value={String(files)} tone="info" icon={RefreshCcw} />
        <MetricCard label="Security warnings" value={String(warnings)} tone={warnings ? "warning" : "success"} icon={AlertTriangle} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Link2 className="h-5 w-5 text-primary" />Approved data sources</CardTitle>
          <CardDescription>Tenant policy enforces allowed domains, supported file types, authentication mode, and scheduled connector permissions.</CardDescription>
        </CardHeader>
        <CardContent>{query.isLoading ? <LoadingState /> : query.isError ? <ErrorState description="Shared links could not be loaded" onRetry={() => query.refetch()} /> : links.length === 0 ? <EmptyState title="No shared links yet" description="Create a source link, validate it, discover supported files, and then create a processing batch." action={<Button asChild><Link to="/app/ingestion/shared-links/new"><Plus className="h-4 w-4" />Create shared link</Link></Button>} /> : <DataTable columns={columns} data={links} searchPlaceholder="Search shared links..." />}</CardContent>
      </Card>
    </>
  );
}
