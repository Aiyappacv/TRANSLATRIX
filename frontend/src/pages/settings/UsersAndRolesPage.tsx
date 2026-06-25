import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Loader2, ShieldCheck, UserPlus } from "lucide-react";
import type { CompanyUser, PermissionMatrixRow, RoleCode } from "@/types";
import { companyApi } from "@/services/companyApi";
import { useAuthStore } from "@/store/authStore";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { roleLabels } from "@/utils/permissions";
import { formatNumber } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";

const assignableRoles = Object.entries(roleLabels).filter(([role]) => role !== "spectra_super_admin") as Array<[RoleCode, string]>;
const permissionMatrix: PermissionMatrixRow[] = [
  { feature: "Company configuration", permissions: { company_owner: "manage", company_admin: "manage", integration_manager: "read", auditor: "read", read_only: "none" } },
  { feature: "Ingestion and files", permissions: { company_owner: "manage", company_admin: "manage", finance_manager: "manage", finance_user: "manage", reviewer: "read", auditor: "read", read_only: "read" } },
  { feature: "Financial entries", permissions: { company_owner: "manage", company_admin: "manage", finance_manager: "manage", finance_user: "manage", reviewer: "manage", approver: "read", auditor: "read", read_only: "read" } },
  { feature: "Review and approval", permissions: { company_owner: "manage", company_admin: "manage", finance_manager: "manage", reviewer: "manage", approver: "manage", auditor: "read", read_only: "read" } },
  { feature: "SAP posting", permissions: { company_owner: "manage", company_admin: "manage", finance_manager: "read", sap_poster: "manage", integration_manager: "read", auditor: "read", read_only: "read" } },
  { feature: "Audit and analytics", permissions: { company_owner: "read", company_admin: "read", finance_manager: "read", auditor: "read", read_only: "read" } },
];

export function UsersAndRolesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const authUser = useAuthStore((state) => state.user);
  const companyId = authUser?.companyId ?? "";
  const companyName = authUser?.companyName ?? "Current company";
  const queryKey = ["company-users", companyId] as const;
  const query = useQuery({ queryKey, queryFn: () => companyApi.getUsers(companyId), enabled: Boolean(companyId) });
  const [invite, setInvite] = useState({ name: "", email: "", role: "finance_user" as RoleCode, department: "Finance", approvalLimit: 0 });
  const [open, setOpen] = useState(false);

  const applyUser = (updated: CompanyUser) => queryClient.setQueryData<CompanyUser[]>(queryKey, (current = []) => current.some((user) => user.id === updated.id) ? current.map((user) => user.id === updated.id ? updated : user) : [...current, updated]);
  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: RoleCode }) => companyApi.updateUserRole(userId, role),
    onSuccess: (updated) => { applyUser(updated); toast.success("Role updated", `${updated.name} is now ${roleLabels[updated.role]}.`); },
    onError: (error) => toast.error("Role update failed", error instanceof Error ? error.message : "Unable to change role."),
  });
  const statusMutation = useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: CompanyUser["status"] }) => companyApi.updateUserStatus(userId, status),
    onSuccess: (updated) => { applyUser(updated); toast.success(`User ${updated.status === "active" ? "activated" : updated.status === "disabled" ? "deactivated" : "updated"}`, `${updated.name}'s access state is persisted.`); },
    onError: (error) => toast.error("Access update failed", error instanceof Error ? error.message : "Unable to update user access."),
  });
  const inviteMutation = useMutation({
    mutationFn: companyApi.inviteUser,
    onSuccess: (created) => {
      applyUser(created);
      setInvite({ name: "", email: "", role: "finance_user", department: "Finance", approvalLimit: 0 });
      setOpen(false);
      toast.success("Invitation created", `${created.email} was added to ${created.companyName} with ${roleLabels[created.role]} access.`);
    },
    onError: (error) => toast.error("Invitation failed", error instanceof Error ? error.message : "Unable to create invitation."),
  });

  const columns = useMemo<ColumnDef<CompanyUser>[]>(() => [
    { accessorKey: "name", header: "User", cell: ({ row }) => <div><p className="font-semibold">{row.original.name}</p><p className="text-xs text-slate-500">{row.original.email}</p></div> },
    { accessorKey: "role", header: "Role", cell: ({ row }) => <select aria-label={`Role for ${row.original.name}`} disabled={roleMutation.isPending && roleMutation.variables?.userId === row.original.id} className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm disabled:opacity-60 dark:border-slate-800 dark:bg-slate-950" value={row.original.role} onChange={(event) => roleMutation.mutate({ userId: row.original.id, role: event.target.value as RoleCode })}>{assignableRoles.map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select> },
    { accessorKey: "department", header: "Department" },
    { accessorKey: "approvalLimit", header: "Approval limit", cell: ({ row }) => <span className="tabular">{formatNumber(row.original.approvalLimit)}</span> },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <Badge variant={row.original.status === "active" ? "success" : row.original.status === "disabled" ? "danger" : "warning"}>{row.original.status}</Badge> },
    { id: "actions", header: "Actions", cell: ({ row }) => { const next = row.original.status === "active" ? "disabled" : "active"; const pending = statusMutation.isPending && statusMutation.variables?.userId === row.original.id; return <Button size="sm" variant="outline" disabled={pending} onClick={() => statusMutation.mutate({ userId: row.original.id, status: next })}>{pending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{pending ? "Updating..." : row.original.status === "active" ? "Deactivate" : "Activate"}</Button>; } },
  ], [roleMutation, statusMutation]);

  const addInvite = () => {
    if (!invite.name.trim() || !/^[^@]+@[^@]+\.[^@]+$/.test(invite.email.trim())) { toast.error("Enter a valid name and email"); return; }
    inviteMutation.mutate({ companyId, companyName, name: invite.name, email: invite.email, role: invite.role, department: invite.department, approvalLimit: invite.approvalLimit });
  };

  return <div className="space-y-6">
    <PageHeader eyebrow="Phase 12 · Administration" title="Users & roles" description="Invite users, assign roles, activate or deactivate access, and review the permission matrix. All changes are submitted through the backend user service." actions={<Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button><UserPlus className="h-4 w-4" />Invite user</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Invite company user</DialogTitle><DialogDescription>Invitation access is restricted to {companyName} and saved through the typed user service.</DialogDescription></DialogHeader><div className="space-y-4"><div><Label>Name</Label><Input className="mt-2" value={invite.name} onChange={(event) => setInvite((value) => ({ ...value, name: event.target.value }))} /></div><div><Label>Email</Label><Input className="mt-2" type="email" value={invite.email} onChange={(event) => setInvite((value) => ({ ...value, email: event.target.value }))} /></div><div><Label>Role</Label><select className="mt-2 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={invite.role} onChange={(event) => setInvite((value) => ({ ...value, role: event.target.value as RoleCode }))}>{assignableRoles.map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select></div><div className="grid gap-4 sm:grid-cols-2"><div><Label>Department</Label><Input className="mt-2" value={invite.department} onChange={(event) => setInvite((value) => ({ ...value, department: event.target.value }))} /></div><div><Label>Approval limit</Label><Input className="mt-2" type="number" min={0} value={invite.approvalLimit} onChange={(event) => setInvite((value) => ({ ...value, approvalLimit: Number(event.target.value) || 0 }))} /></div></div><Button className="w-full" disabled={inviteMutation.isPending} onClick={addInvite}>{inviteMutation.isPending ? "Creating invitation..." : "Create invitation"}</Button></div></DialogContent></Dialog>} />
    {query.isLoading ? <LoadingState /> : <DataTable columns={columns} data={query.data ?? []} searchPlaceholder="Search users and roles..." exportFileName="company-users" />}
    <Card><CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" />Permission matrix</CardTitle><CardDescription>High-level least-privilege access. Backend authorization remains authoritative.</CardDescription></CardHeader><CardContent className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-sm"><thead className="text-xs uppercase tracking-wide text-slate-500"><tr><th className="pb-3">Feature</th>{assignableRoles.map(([role, label]) => <th key={role} className="pb-3 text-center">{label}</th>)}</tr></thead><tbody>{permissionMatrix.map((row) => <tr key={row.feature} className="border-t border-slate-100 dark:border-slate-800"><td className="py-3 font-semibold">{row.feature}</td>{assignableRoles.map(([role]) => { const value = row.permissions[role] ?? "none"; return <td key={role} className="py-3 text-center"><Badge variant={value === "manage" ? "success" : value === "read" ? "info" : "neutral"}>{value}</Badge></td>; })}</tr>)}</tbody></table></CardContent></Card>
  </div>;
}
