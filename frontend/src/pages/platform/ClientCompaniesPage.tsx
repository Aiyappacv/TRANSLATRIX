import { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Building2, Crown, Plus, UsersRound, WalletCards } from "lucide-react";
import type { Company, CompanyUser } from "@/types";
import { companyApi } from "@/services/companyApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatNumber, formatPercent } from "@/utils/formatters";
import { roleLabels } from "@/utils/permissions";

const companyColumns: ColumnDef<Company>[] = [
  { accessorKey: "legalName", header: "Client company", cell: ({ row }) => <div><p className="font-semibold">{row.original.legalName}</p><p className="text-xs text-slate-500">{row.original.industry} · {row.original.country}</p></div> },
  { accessorKey: "companyAdminEmail", header: "Company admin" },
  { accessorKey: "defaultCompanyCode", header: "Company code" },
  { accessorKey: "plan", header: "Plan", cell: ({ row }) => <Badge variant="brand">{row.original.plan ?? "Growth"}</Badge> },
  { accessorKey: "tokenUsage", header: "Token usage", cell: ({ row }) => `${formatNumber(row.original.tokenUsage ?? 0)} / ${formatNumber(row.original.tokenLimit ?? 0)}` },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status === "active" ? "completed" : "draft"} /> },
];

const userColumns: ColumnDef<CompanyUser>[] = [
  { accessorKey: "name", header: "User", cell: ({ row }) => <div><p className="font-semibold">{row.original.name}</p><p className="text-xs text-slate-500">{row.original.email}</p></div> },
  { accessorKey: "companyName", header: "Company" },
  { accessorKey: "role", header: "Role", cell: ({ row }) => <Badge variant={row.original.role === "company_admin" ? "info" : "neutral"}>{roleLabels[row.original.role]}</Badge> },
  { accessorKey: "department", header: "Department" },
  { accessorKey: "approvalLimit", header: "Approval limit", cell: ({ row }) => formatNumber(row.original.approvalLimit) },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <Badge variant={row.original.status === "active" ? "success" : "neutral"}>{row.original.status}</Badge> },
];

export function ClientCompaniesPage() {
  const companies = useQuery({ queryKey: ["companies"], queryFn: companyApi.getCompanies });
  const users = useQuery({ queryKey: ["company-users"], queryFn: () => companyApi.getUsers() });

  if (companies.isLoading || users.isLoading) return <LoadingState />;

  const clientCompanies = (companies.data ?? []).filter((company) => company.id !== "company_spectra_ai");
  const clientUsers = users.data ?? [];
  const totalTokenLimit = clientCompanies.reduce((sum, company) => sum + (company.tokenLimit ?? 0), 0);
  const totalTokenUsage = clientCompanies.reduce((sum, company) => sum + (company.tokenUsage ?? 0), 0);

  return (
    <>
      <PageHeader
        eyebrow="SPECTRA AI platform owner"
        title="Client companies"
        description="Super admin view for registering client companies, monitoring usage, and verifying each company admin and role user."
        actions={<Button asChild><Link to="/super-admin/company-onboarding"><Plus className="h-4 w-4" />Register client company</Link></Button>}
      />

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Client companies" value={String(clientCompanies.length)} tone="info" icon={Building2} />
        <MetricCard label="Company users" value={String(clientUsers.length)} tone="success" icon={UsersRound} />
        <MetricCard label="Token usage" value={formatNumber(totalTokenUsage)} tone="warning" icon={WalletCards} />
        <MetricCard label="Usage ratio" value={formatPercent(totalTokenUsage / Math.max(totalTokenLimit, 1))} tone="neutral" icon={Crown} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registered client companies</CardTitle>
          <CardDescription>The platform owner registers and manages client company tenants from this workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable columns={companyColumns} data={clientCompanies} searchPlaceholder="Search client companies..." />
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Company admins and assigned subroles</CardTitle>
          <CardDescription>Each client company admin can assign finance manager, finance user, reviewer, approver, SAP poster, integration manager, and auditor roles.</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable columns={userColumns} data={clientUsers} searchPlaceholder="Search company users..." />
        </CardContent>
      </Card>
    </>
  );
}
