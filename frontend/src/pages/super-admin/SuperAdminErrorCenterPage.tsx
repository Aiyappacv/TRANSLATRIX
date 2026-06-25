import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertOctagon, Bug, CircleCheckBig, Plus, TriangleAlert } from "lucide-react";
import type { PlatformErrorRecord, PlatformIncidentInput } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { DataTable } from "@/components/common/DataTable";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { useToast } from "@/hooks/useToast";
import { formatDateTime, formatNumber } from "@/utils/formatters";

const initialIncident: PlatformIncidentInput = { title: "", severity: "high", source: "Platform operations", message: "", owner: "Platform Operations" };

export function SuperAdminErrorCenterPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [investigation, setInvestigation] = useState<PlatformErrorRecord | null>(null);
  const [owner, setOwner] = useState("Platform Operations");
  const [notes, setNotes] = useState("");
  const [incidentOpen, setIncidentOpen] = useState(false);
  const [incident, setIncident] = useState<PlatformIncidentInput>(initialIncident);
  const errors = useQuery({ queryKey: ["super-admin", "errors"], queryFn: superAdminApi.getErrors });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["super-admin", "errors"] }),
      queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] }),
    ]);
  };
  const investigate = useMutation({
    mutationFn: ({ errorId, owner: assignedOwner, notes: detail }: { errorId: string; owner: string; notes: string }) => superAdminApi.investigateError(errorId, assignedOwner, detail),
    onSuccess: async (record) => {
      await refresh();
      setInvestigation(null);
      setNotes("");
      toast.success("Investigation started", `${record.code} assigned to ${record.owner}.`);
    },
    onError: (error) => toast.error("Unable to start investigation", error instanceof Error ? error.message : "Unexpected error."),
  });
  const createIncident = useMutation({
    mutationFn: superAdminApi.createIncident,
    onSuccess: async (record) => {
      await refresh();
      setIncidentOpen(false);
      setIncident(initialIncident);
      toast.success("Incident created", `${record.code} is now under investigation.`);
    },
    onError: (error) => toast.error("Unable to create incident", error instanceof Error ? error.message : "Unexpected error."),
  });
  const columns = useMemo<ColumnDef<PlatformErrorRecord>[]>(() => [
    { accessorKey: "title", header: "Error", cell: ({ row }) => <div className="max-w-md"><p className="font-semibold">{row.original.title}</p><p className="mt-1 text-xs text-slate-500">{row.original.code} · {row.original.correlationId}</p></div> },
    { accessorKey: "severity", header: "Severity", cell: ({ row }) => <PlatformStatusBadge status={row.original.severity} /> },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <PlatformStatusBadge status={row.original.status} /> },
    { accessorKey: "source", header: "Source" },
    { accessorKey: "companyName", header: "Tenant", cell: ({ row }) => row.original.companyName ?? "Platform" },
    { accessorKey: "occurrences", header: "Occurrences", cell: ({ row }) => formatNumber(row.original.occurrences) },
    { accessorKey: "lastSeenAt", header: "Last seen", cell: ({ row }) => formatDateTime(row.original.lastSeenAt) },
    { accessorKey: "owner", header: "Owner", cell: ({ row }) => row.original.owner ?? "Unassigned" },
    { id: "actions", header: "Actions", cell: ({ row }) => <Button variant="outline" size="sm" onClick={() => { setInvestigation(row.original); setOwner(row.original.owner ?? "Platform Operations"); setNotes(""); }}>Investigate</Button> },
  ], []);
  if (errors.isLoading) return <LoadingState label="Loading platform errors..." />;
  const data = errors.data ?? [];
  return (
    <>
      <PageHeader eyebrow="Operational incident management" title="Error center" description="Correlate provider, tenant, queue, and posting errors without exposing secrets or unredacted financial payloads." actions={<Button onClick={() => setIncidentOpen(true)}><Plus className="h-4 w-4" />Create incident</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Open errors" value={String(data.filter((error) => error.status !== "resolved").length)} tone="danger" icon={Bug} />
        <MetricCard label="Critical" value={String(data.filter((error) => error.severity === "critical").length)} tone="danger" icon={AlertOctagon} />
        <MetricCard label="Investigating" value={String(data.filter((error) => error.status === "investigating").length)} tone="warning" icon={TriangleAlert} />
        <MetricCard label="Resolved" value={String(data.filter((error) => error.status === "resolved").length)} tone="success" icon={CircleCheckBig} />
      </div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search errors, codes, tenants, correlation IDs..." exportFileName="platform-errors" /></CardContent></Card>

      <Dialog open={Boolean(investigation)} onOpenChange={(open) => !open && setInvestigation(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Investigate {investigation?.code}</DialogTitle><DialogDescription>{investigation?.title}. Assignment and notes are written to the immutable platform audit log.</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label htmlFor="investigation-owner">Owner</Label><Input id="investigation-owner" value={owner} onChange={(event) => setOwner(event.target.value)} /></div>
            <div className="space-y-2"><Label htmlFor="investigation-notes">Investigation notes</Label><Textarea id="investigation-notes" className="min-h-28" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record the initial triage findings and next action." /></div>
            <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setInvestigation(null)}>Cancel</Button><Button disabled={!investigation || !owner.trim() || investigate.isPending} onClick={() => investigation && investigate.mutate({ errorId: investigation.id, owner, notes })}>{investigate.isPending ? "Assigning..." : "Start investigation"}</Button></div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={incidentOpen} onOpenChange={setIncidentOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Create platform incident</DialogTitle><DialogDescription>Create a traceable incident record for a newly reported provider, queue, integration, or tenant failure.</DialogDescription></DialogHeader>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-2"><Label htmlFor="incident-title">Incident title</Label><Input id="incident-title" value={incident.title} onChange={(event) => setIncident((value) => ({ ...value, title: event.target.value }))} /></div>
            <div className="space-y-2"><Label>Severity</Label><Select value={incident.severity} onValueChange={(value) => setIncident((current) => ({ ...current, severity: value as PlatformIncidentInput["severity"] }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["critical", "high", "medium", "low"].map((severity) => <SelectItem key={severity} value={severity}>{severity}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label htmlFor="incident-source">Source</Label><Input id="incident-source" value={incident.source} onChange={(event) => setIncident((value) => ({ ...value, source: event.target.value }))} /></div>
            <div className="space-y-2"><Label htmlFor="incident-company">Tenant name (optional)</Label><Input id="incident-company" value={incident.companyName ?? ""} onChange={(event) => setIncident((value) => ({ ...value, companyName: event.target.value || undefined }))} /></div>
            <div className="space-y-2"><Label htmlFor="incident-owner">Owner</Label><Input id="incident-owner" value={incident.owner} onChange={(event) => setIncident((value) => ({ ...value, owner: event.target.value }))} /></div>
            <div className="space-y-2 md:col-span-2"><Label htmlFor="incident-message">Description</Label><Textarea id="incident-message" className="min-h-28" value={incident.message} onChange={(event) => setIncident((value) => ({ ...value, message: event.target.value }))} /></div>
          </div>
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setIncidentOpen(false)}>Cancel</Button><Button disabled={!incident.title.trim() || !incident.message.trim() || !incident.owner.trim() || createIncident.isPending} onClick={() => createIncident.mutate(incident)}>{createIncident.isPending ? "Creating..." : "Create incident"}</Button></div>
        </DialogContent>
      </Dialog>
    </>
  );
}
