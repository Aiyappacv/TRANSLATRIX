import { useQuery } from "@tanstack/react-query";
import type { RoleCode } from "@/types";
import { dashboardApi } from "@/services/dashboardApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import {
  AuditActivityCard,
  CategoryBreakdownChart,
  DashboardKpiGrid,
  IntegrationStatusCard,
  MyTasksCard,
  PendingReviewCard,
  ProcessingStatusCard,
  QuickActionsPanel,
  RecentEntriesTable,
  RecentFilesCard,
  SapPostingStatusCard,
  ValidationIssuesCard,
} from "@/components/dashboard/RoleDashboardWidgets";

export function RoleDashboardPage({ role }: { role: RoleCode }) {
  const query = useQuery({
    queryKey: ["role-dashboard", role],
    queryFn: () => dashboardApi.getRoleDashboard(role),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
  });
  if (query.isLoading) return <LoadingState label="Loading role dashboard..." />;
  if (query.isError || !query.data) return <ErrorState title="Dashboard unavailable" description={query.error instanceof Error ? query.error.message : "Unable to load dashboard data."} onRetry={() => query.refetch()} />;
  const definition = query.data;
  return <div className="space-y-6">
    <PageHeader eyebrow="Phase 11 · Role-wise dashboard" title={definition.title} description={definition.subtitle} actions={<div className="flex gap-2"><Badge variant="info">Focus: {definition.focus}</Badge>{definition.readOnly ? <Badge variant="neutral">Read-only</Badge> : null}</div>} />
    <DashboardKpiGrid kpis={definition.kpis} />
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]"><MyTasksCard tasks={definition.tasks} /><QuickActionsPanel actions={definition.quickActions} readOnly={definition.readOnly} /></div>
    <div className="grid gap-6 xl:grid-cols-3"><ProcessingStatusCard items={definition.processing} /><SapPostingStatusCard items={definition.sapPosting} /><ValidationIssuesCard items={definition.validation} /></div>
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]"><RecentEntriesTable entries={definition.recentEntries} /><CategoryBreakdownChart data={definition.categoryBreakdown} /></div>
    <div className="grid gap-6 xl:grid-cols-3"><RecentFilesCard files={definition.recentFiles} /><IntegrationStatusCard items={definition.integrations} /><AuditActivityCard events={definition.auditActivity} /></div>
    <PendingReviewCard definition={definition} />
  </div>;
}
