import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { CheckCircle2, History, ListChecks, MessageSquareWarning, UserCheck, XCircle } from "lucide-react";
import type { ApprovalHistoryEvent, ReviewDecisionType } from "@/types";
import { reviewApi } from "@/services/reviewApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { DataTable } from "@/components/common/DataTable";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDateTime } from "@/utils/formatters";

type DecisionFilter = "all" | ReviewDecisionType;

const decisionLabels: Record<ReviewDecisionType, string> = {
  task_created: "Task created",
  assigned: "Assigned",
  review_started: "Review started",
  field_changed: "Field changed",
  checklist_updated: "Checklist updated",
  comment_added: "Comment added",
  approved: "Approved",
  rejected: "Rejected",
  changes_requested: "Changes requested",
  second_approval_requested: "Second approval requested",
  exported: "Exported",
  sap_failed: "SAP failed",
};

const decisionFilters: Array<{ value: DecisionFilter; label: string }> = [
  { value: "all", label: "All decisions" },
  ...Object.entries(decisionLabels).map(([value, label]) => ({ value: value as ReviewDecisionType, label })),
];

function decisionVariant(decision: ReviewDecisionType) {
  if (decision === "approved") return "success" as const;
  if (["rejected", "sap_failed"].includes(decision)) return "danger" as const;
  if (["changes_requested", "second_approval_requested"].includes(decision)) return "warning" as const;
  if (["assigned", "review_started"].includes(decision)) return "brand" as const;
  return "neutral" as const;
}

function DecisionIcon({ decision }: { decision: ReviewDecisionType }) {
  if (decision === "approved") return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (decision === "rejected") return <XCircle className="h-4 w-4 text-red-600" />;
  if (decision === "changes_requested") return <MessageSquareWarning className="h-4 w-4 text-amber-600" />;
  if (decision === "second_approval_requested") return <UserCheck className="h-4 w-4 text-amber-600" />;
  return <History className="h-4 w-4 text-primary" />;
}

export function ApprovalHistoryPage() {
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("all");
  const query = useQuery({ queryKey: ["approval-history"], queryFn: () => reviewApi.getApprovalHistory() });

  const events = useMemo(() => {
    const all = query.data ?? [];
    return decisionFilter === "all" ? all : all.filter((event) => event.decision === decisionFilter);
  }, [decisionFilter, query.data]);

  const columns = useMemo<ColumnDef<ApprovalHistoryEvent>[]>(
    () => [
      { accessorKey: "timestamp", header: "Timestamp", cell: ({ row }) => <span className="whitespace-nowrap text-sm text-slate-500">{formatDateTime(row.original.timestamp)}</span> },
      {
        accessorKey: "entryId",
        header: "Entry",
        cell: ({ row }) => <div><Link to={`/app/review/${row.original.taskId}`} className="font-semibold text-primary hover:underline">{row.original.entryId}</Link><p className="text-xs text-slate-500">{row.original.taskId}</p></div>,
      },
      { accessorKey: "actor", header: "Changed by", cell: ({ row }) => <div><p className="font-medium">{row.original.actor}</p><p className="text-xs text-slate-500">{row.original.actorRole}</p></div> },
      { accessorKey: "decision", header: "Decision", cell: ({ row }) => <Badge variant={decisionVariant(row.original.decision)}>{decisionLabels[row.original.decision]}</Badge> },
      { accessorKey: "field", header: "Field", cell: ({ row }) => row.original.field ?? "—" },
      { accessorKey: "oldValue", header: "Old value", cell: ({ row }) => <p className="max-w-[240px] whitespace-normal text-slate-500">{row.original.oldValue ?? "—"}</p> },
      { accessorKey: "newValue", header: "New value", cell: ({ row }) => <p className="max-w-[240px] whitespace-normal font-medium">{row.original.newValue ?? "—"}</p> },
      { accessorKey: "comments", header: "Comments", cell: ({ row }) => <p className="max-w-[300px] whitespace-normal text-slate-500">{row.original.comments ?? "—"}</p> },
    ],
    [],
  );

  const approvedCount = (query.data ?? []).filter((event) => event.decision === "approved").length;
  const rejectedCount = (query.data ?? []).filter((event) => event.decision === "rejected").length;
  const changedCount = (query.data ?? []).filter((event) => ["field_changed", "checklist_updated", "comment_added"].includes(event.decision)).length;

  return (
    <>
      <PageHeader
        eyebrow="Human review"
        title="Approval history"
        description="Persistent timeline of every decision, actor, field change, old value, new value, timestamp, and reviewer comment."
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-slate-500">All events</p><p className="mt-2 text-2xl font-bold">{query.data?.length ?? 0}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Approvals</p><p className="mt-2 text-2xl font-bold text-emerald-600">{approvedCount}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Rejections</p><p className="mt-2 text-2xl font-bold text-red-600">{rejectedCount}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Review changes</p><p className="mt-2 text-2xl font-bold">{changedCount}</p></CardContent></Card>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><History className="h-5 w-5 text-primary" />Decision timeline</CardTitle>
          <CardDescription>Newest actions appear first. Entries are written when users assign, edit, approve, reject, request corrections, request second approval, or export.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="max-w-sm">
            <Select value={decisionFilter} onValueChange={(value) => setDecisionFilter(value as DecisionFilter)}>
              <SelectTrigger><SelectValue placeholder="Filter decisions" /></SelectTrigger>
              <SelectContent>{decisionFilters.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          {query.isLoading ? <LoadingState /> : query.isError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{query.error instanceof Error ? query.error.message : "Unable to load approval history."}</div>
          ) : events.length ? (
            <div className="space-y-3">
              {events.slice(0, 8).map((event) => (
                <div key={event.id} className="relative rounded-2xl border border-slate-200 p-4 pl-12 dark:border-slate-800">
                  <div className="absolute left-4 top-4 flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-900"><DecisionIcon decision={event.decision} /></div>
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2"><Badge variant={decisionVariant(event.decision)}>{decisionLabels[event.decision]}</Badge><Link to={`/app/review/${event.taskId}`} className="text-sm font-semibold text-primary hover:underline">{event.entryId}</Link></div>
                      <p className="mt-2 text-sm"><span className="font-semibold">{event.actor}</span> · {event.actorRole}</p>
                      {event.field ? <p className="mt-1 text-sm text-slate-500">{event.field}: <span className="line-through">{event.oldValue ?? "—"}</span> → <span className="font-medium text-slate-800 dark:text-slate-200">{event.newValue ?? "—"}</span></p> : null}
                      {event.comments ? <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{event.comments}</p> : null}
                    </div>
                    <p className="whitespace-nowrap text-xs text-slate-500">{formatDateTime(event.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">No approval events match this filter.</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ListChecks className="h-5 w-5 text-primary" />Complete audit table</CardTitle>
          <CardDescription>Search across entry, actor, decision, field, old/new values, and comments.</CardDescription>
        </CardHeader>
        <CardContent>{query.isLoading ? <LoadingState /> : <DataTable data={events} columns={columns} searchPlaceholder="Search approval history..." dense />}</CardContent>
      </Card>
    </>
  );
}
