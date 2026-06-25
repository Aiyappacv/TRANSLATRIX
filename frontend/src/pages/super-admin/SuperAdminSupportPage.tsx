import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheckBig, LifeBuoy, MessagesSquare, Plus, Siren } from "lucide-react";
import type { SupportTicket, SupportTicketInput } from "@/types";
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
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

const initialCase: SupportTicketInput = { companyId: "", companyName: "", subject: "", priority: "normal", owner: "Platform Support" };

export function SuperAdminSupportPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<SupportTicket | null>(null);
  const [status, setStatus] = useState<SupportTicket["status"]>("new");
  const [owner, setOwner] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newCase, setNewCase] = useState<SupportTicketInput>(initialCase);
  const tickets = useQuery({ queryKey: ["super-admin", "support"], queryFn: superAdminApi.getSupportTickets });
  const companies = useQuery({ queryKey: ["super-admin", "companies"], queryFn: superAdminApi.getCompanies });
  const refresh = async () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["super-admin", "support"] }),
    queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] }),
  ]);
  const create = useMutation({
    mutationFn: superAdminApi.createSupportTicket,
    onSuccess: async (ticket) => { await refresh(); setCreateOpen(false); setNewCase(initialCase); toast.success("Support case created", `${ticket.id} was added to the platform support queue.`); },
    onError: (error) => toast.error("Case creation failed", error instanceof Error ? error.message : "Unable to create support case."),
  });
  const update = useMutation({
    mutationFn: ({ id, nextStatus, nextOwner }: { id: string; nextStatus: SupportTicket["status"]; nextOwner?: string }) => superAdminApi.updateSupportTicket(id, { status: nextStatus, owner: nextOwner }),
    onSuccess: async (ticket) => { await refresh(); setSelected(ticket); toast.success("Ticket updated", `${ticket.id} is now ${ticket.status.replaceAll("_", " ")}.`); },
    onError: (error) => toast.error("Ticket update failed", error instanceof Error ? error.message : "Unable to update ticket."),
  });
  const columns = useMemo<ColumnDef<SupportTicket>[]>(() => [
    { accessorKey: "id", header: "Ticket" },
    { accessorKey: "subject", header: "Subject", cell: ({ row }) => <p className="max-w-sm font-semibold">{row.original.subject}</p> },
    { accessorKey: "companyName", header: "Company" },
    { accessorKey: "priority", header: "Priority", cell: ({ row }) => <PlatformStatusBadge status={row.original.priority} /> },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <PlatformStatusBadge status={row.original.status} /> },
    { accessorKey: "owner", header: "Owner", cell: ({ row }) => row.original.owner ?? "Unassigned" },
    { accessorKey: "updatedAt", header: "Updated", cell: ({ row }) => formatDateTime(row.original.updatedAt) },
    { id: "actions", header: "Actions", cell: ({ row }) => <Button variant="outline" size="sm" onClick={() => { setSelected(row.original); setStatus(row.original.status); setOwner(row.original.owner ?? ""); }}>Open ticket</Button> },
  ], []);
  if (tickets.isLoading || companies.isLoading) return <LoadingState label="Loading support tickets..." />;
  const data = tickets.data ?? [];
  const submitCase = () => {
    if (!newCase.companyId || !newCase.subject.trim()) { toast.error("Select a company and enter a subject"); return; }
    create.mutate(newCase);
  };
  return (
    <>
      <PageHeader eyebrow="Customer operations" title="Platform support" description="Manage company support requests with controlled, time-bound, and fully audited tenant access." actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" />New support case</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-4"><MetricCard label="Open tickets" value={String(data.filter((ticket) => ticket.status !== "resolved").length)} icon={LifeBuoy} /><MetricCard label="Urgent" value={String(data.filter((ticket) => ticket.priority === "urgent").length)} tone="danger" icon={Siren} /><MetricCard label="Waiting customer" value={String(data.filter((ticket) => ticket.status === "waiting_customer").length)} tone="warning" icon={MessagesSquare} /><MetricCard label="Resolved" value={String(data.filter((ticket) => ticket.status === "resolved").length)} tone="success" icon={CircleCheckBig} /></div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search tickets, companies, subjects, owners..." exportFileName="platform-support" /></CardContent></Card>

      <Dialog open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}><DialogContent><DialogHeader><DialogTitle>{selected?.id}</DialogTitle><DialogDescription>{selected?.companyName} · created {selected ? formatDateTime(selected.createdAt) : ""}</DialogDescription></DialogHeader>{selected ? <div className="space-y-4"><div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-900"><p className="font-semibold">{selected.subject}</p><div className="mt-3 flex gap-2"><PlatformStatusBadge status={selected.priority} /><PlatformStatusBadge status={selected.status} /></div></div><div className="space-y-2"><Label>Status</Label><Select value={status} onValueChange={(value) => setStatus(value as SupportTicket["status"])}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="new">New</SelectItem><SelectItem value="in_progress">In progress</SelectItem><SelectItem value="waiting_customer">Waiting customer</SelectItem><SelectItem value="resolved">Resolved</SelectItem></SelectContent></Select></div><div className="space-y-2"><Label htmlFor="ticket-owner">Owner</Label><Input id="ticket-owner" value={owner} onChange={(event) => setOwner(event.target.value)} /></div><div className="flex justify-end"><Button disabled={update.isPending} onClick={() => update.mutate({ id: selected.id, nextStatus: status, nextOwner: owner || undefined })}>{update.isPending ? "Saving..." : "Save ticket"}</Button></div></div> : null}</DialogContent></Dialog>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogContent><DialogHeader><DialogTitle>New support case</DialogTitle><DialogDescription>Create a tenant-scoped support request. Any later tenant access remains separately authorized and audited.</DialogDescription></DialogHeader><div className="space-y-4"><div className="space-y-2"><Label>Company</Label><Select value={newCase.companyId} onValueChange={(companyId) => { const company = (companies.data ?? []).find((item) => item.id === companyId); setNewCase((current) => ({ ...current, companyId, companyName: company?.companyName ?? "" })); }}><SelectTrigger><SelectValue placeholder="Select tenant" /></SelectTrigger><SelectContent>{(companies.data ?? []).map((company) => <SelectItem key={company.id} value={company.id}>{company.companyName}</SelectItem>)}</SelectContent></Select></div><div className="space-y-2"><Label htmlFor="case-subject">Subject</Label><Input id="case-subject" value={newCase.subject} onChange={(event) => setNewCase((current) => ({ ...current, subject: event.target.value }))} /></div><div className="space-y-2"><Label>Priority</Label><Select value={newCase.priority} onValueChange={(priority) => setNewCase((current) => ({ ...current, priority: priority as SupportTicket["priority"] }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="urgent">Urgent</SelectItem><SelectItem value="high">High</SelectItem><SelectItem value="normal">Normal</SelectItem><SelectItem value="low">Low</SelectItem></SelectContent></Select></div><div className="space-y-2"><Label htmlFor="case-owner">Initial owner</Label><Input id="case-owner" value={newCase.owner ?? ""} onChange={(event) => setNewCase((current) => ({ ...current, owner: event.target.value }))} /></div><div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button disabled={create.isPending} onClick={submitCase}>{create.isPending ? "Creating..." : "Create case"}</Button></div></div></DialogContent></Dialog>
    </>
  );
}
