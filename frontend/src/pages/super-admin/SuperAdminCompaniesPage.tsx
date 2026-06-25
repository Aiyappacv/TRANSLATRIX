import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { Building2, Plus, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import type { PlatformCompany } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { DataTable } from "@/components/common/DataTable";
import { LoadingState } from "@/components/common/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { formatDate, formatDateTime, formatNumber } from "@/utils/formatters";

const columns: ColumnDef<PlatformCompany>[] = [
  { accessorKey: "companyName", header: "Company", cell: ({ row }) => <div><Link to={`/super-admin/companies/${row.original.id}`} className="font-semibold text-primary hover:underline">{row.original.companyName}</Link><p className="text-xs text-slate-500">{row.original.tenantId}</p></div> },
  { accessorKey: "country", header: "Country" },
  { accessorKey: "industry", header: "Industry" },
  { accessorKey: "plan", header: "Plan" },
  { accessorKey: "status", header: "Status", cell: ({ row }) => <PlatformStatusBadge status={row.original.status} /> },
  { accessorKey: "users", header: "Users", cell: ({ row }) => formatNumber(row.original.users) },
  { accessorKey: "filesProcessed", header: "Files processed", cell: ({ row }) => formatNumber(row.original.filesProcessed) },
  { accessorKey: "entriesProcessed", header: "Entries processed", cell: ({ row }) => formatNumber(row.original.entriesProcessed) },
  { accessorKey: "sapPostings", header: "SAP postings", cell: ({ row }) => formatNumber(row.original.sapPostings) },
  { accessorKey: "storageUsedGb", header: "Storage", cell: ({ row }) => `${formatNumber(row.original.storageUsedGb)} GB` },
  { accessorKey: "createdAt", header: "Created", cell: ({ row }) => formatDate(row.original.createdAt) },
  { accessorKey: "lastActivityAt", header: "Last activity", cell: ({ row }) => formatDateTime(row.original.lastActivityAt) },
  { id: "actions", header: "Actions", cell: ({ row }) => <Button asChild variant="outline" size="sm"><Link to={`/super-admin/companies/${row.original.id}`}>View tenant</Link></Button> },
];

export function SuperAdminCompaniesPage() {
  const companies = useQuery({ queryKey: ["super-admin", "companies"], queryFn: superAdminApi.getCompanies });
  if (companies.isLoading) return <LoadingState label="Loading companies..." />;
  const data = companies.data ?? [];
  return (
    <>
      <PageHeader eyebrow="Tenant administration" title="Company management" description="Manage tenant lifecycle, plans, usage, access posture, and operational activity across the platform." actions={<Button asChild><Link to="/super-admin/company-onboarding"><Plus className="h-4 w-4" />Onboard company</Link></Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Total companies" value={String(data.length)} icon={Building2} />
        <MetricCard label="Active" value={String(data.filter((company) => company.status === "active").length)} tone="success" icon={Building2} />
        <MetricCard label="Trials" value={String(data.filter((company) => company.status === "trial").length)} tone="warning" icon={Building2} />
        <MetricCard label="Platform users" value={formatNumber(data.reduce((sum, company) => sum + company.users, 0))} tone="info" icon={UsersRound} />
      </div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search company, tenant ID, country, plan..." /></CardContent></Card>
    </>
  );
}
