import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  CheckCircle2,
  ClipboardCheck,
  Download,
  MessageSquareWarning,
  SlidersHorizontal,
  UserPlus,
  XCircle,
} from "lucide-react";
import type { ReviewActor, ReviewBulkAction, ReviewBulkActionInput, ReviewTask, ReviewTaskStatus } from "@/types";
import { reviewApi } from "@/services/reviewApi";
import { companyApi } from "@/services/companyApi";
import { useAuthStore } from "@/store/authStore";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { EmptyState } from "@/components/common/EmptyState";
import { DataTable } from "@/components/common/DataTable";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { CategoryBadge } from "@/components/common/CategoryBadge";
import { ReviewStatusBadge } from "@/components/review/ReviewStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { usePermissions } from "@/hooks/usePermissions";
import { useToast } from "@/hooks/useToast";
import { permissions, roleLabels } from "@/utils/permissions";
import { formatCurrency, formatDateTime } from "@/utils/formatters";

type StatusFilter = "all" | ReviewTaskStatus;
type DialogAction = Exclude<ReviewBulkAction, "export"> | null;

const statusFilters: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "All review tasks" },
  { value: "pending_review", label: "Pending review" },
  { value: "in_review", label: "In review" },
  { value: "validation_failed", label: "Validation failed" },
  { value: "low_confidence", label: "Low confidence" },
  { value: "ready_for_approval", label: "Ready for approval" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "sap_failed", label: "SAP failed" },
  { value: "changes_requested", label: "Changes requested" },
  { value: "second_approval", label: "Second approval" },
];

function csvCell(value: unknown) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function exportTasks(tasks: ReviewTask[]) {
  const headers = [
    "Task ID",
    "Entry ID",
    "Source file",
    "English description",
    "Amount",
    "Currency",
    "Category",
    "SAP T-Code",
    "Review status",
    "Assigned reviewer",
    "Confidence",
    "Updated at",
  ];
  const rows = tasks.map((task) => [
    task.taskId,
    task.entry.entryId,
    task.entry.sourceFile,
    task.entry.englishDescription,
    task.entry.amount,
    task.entry.currency,
    task.entry.category,
    task.entry.sapTCode,
    task.status,
    task.assignedReviewer,
    task.entry.confidence?.overall ?? 0,
    task.updatedAt,
  ]);
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `translatrix-review-export-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReviewQueuePage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const user = useAuthStore((state) => state.user);
  const { hasPermission } = usePermissions();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [dialogAction, setDialogAction] = useState<DialogAction>(null);
  const [selectedReviewer, setSelectedReviewer] = useState("");
  const [comments, setComments] = useState("");

  const tasksQuery = useQuery({ queryKey: ["review-tasks"], queryFn: reviewApi.getTasks });
  const usersQuery = useQuery({
    queryKey: ["review-reviewers", user?.companyId],
    queryFn: () => companyApi.getUsers(user?.companyId),
    enabled: Boolean(user?.companyId),
  });

  const actor: ReviewActor = {
    id: user?.id ?? "anonymous",
    name: user?.name ?? "Unknown user",
    role: user?.roles[0] ? (roleLabels[user.roles[0]] ?? user.roles[0]) : "Unknown role",
  };

  const tasks = useMemo(() => tasksQuery.data ?? [], [tasksQuery.data]);
  const visibleTasks = useMemo(
    () => (statusFilter === "all" ? tasks : tasks.filter((task) => task.status === statusFilter)),
    [statusFilter, tasks],
  );
  const selectedTasks = useMemo(() => tasks.filter((task) => selectedIds.includes(task.id)), [selectedIds, tasks]);

  const reviewerOptions = useMemo(() => {
    const users = (usersQuery.data ?? [])
      .filter((item) => ["reviewer", "approver", "finance_manager", "company_admin"].includes(item.role) && item.status === "active")
      .map((item) => ({ id: item.id, name: item.name, role: roleLabels[item.role] ?? item.role }));
    const existing = tasks
      .filter((task) => task.assignedReviewer !== "Unassigned")
      .map((task) => ({ id: task.assignedReviewerId ?? task.assignedReviewer, name: task.assignedReviewer, role: task.reviewerGroup }));
    return [...users, ...existing].filter((item, index, list) => list.findIndex((other) => other.name === item.name) === index);
  }, [tasks, usersQuery.data]);

  const bulkMutation = useMutation({
    mutationFn: (input: ReviewBulkActionInput) => reviewApi.bulkAction(input),
    onSuccess: async (result, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["approval-history"] }),
      ]);
      if (variables.action === "export") exportTasks(selectedTasks);
      if (result.succeeded.length) toast.success("Bulk action completed", `${result.succeeded.length} review task(s) updated.`);
      if (result.failed.length) toast.warning("Some tasks were not updated", result.failed.map((item) => item.reason).join(" "));
      setSelectedIds([]);
      setDialogAction(null);
      setComments("");
      setSelectedReviewer("");
    },
    onError: (error) => toast.error("Review action failed", error instanceof Error ? error.message : "Unknown error"),
  });

  const submitAction = (action: ReviewBulkAction) => {
    if (!selectedIds.length) return;
    const reviewer = reviewerOptions.find((item) => item.id === selectedReviewer);
    bulkMutation.mutate({
      taskIds: selectedIds,
      action,
      actor,
      reviewerId: reviewer?.id,
      reviewerName: reviewer?.name,
      comments: comments.trim() || undefined,
    });
  };

  const statusCounts = useMemo(
    () => Object.fromEntries(statusFilters.map((filter) => [filter.value, filter.value === "all" ? tasks.length : tasks.filter((task) => task.status === filter.value).length])),
    [tasks],
  );

  const columns = useMemo<ColumnDef<ReviewTask>[]>(
    () => [
      {
        id: "select",
        header: () => (
          <Checkbox
            aria-label="Select visible review tasks"
            checked={visibleTasks.length > 0 && visibleTasks.every((task) => selectedIds.includes(task.id))}
            onChange={(event) =>
              setSelectedIds((current) =>
                event.target.checked
                  ? Array.from(new Set([...current, ...visibleTasks.map((task) => task.id)]))
                  : current.filter((id) => !visibleTasks.some((task) => task.id === id)),
              )
            }
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            aria-label={`Select ${row.original.taskId}`}
            checked={selectedIds.includes(row.original.id)}
            onChange={(event) =>
              setSelectedIds((current) =>
                event.target.checked ? [...current, row.original.id] : current.filter((id) => id !== row.original.id),
              )
            }
          />
        ),
      },
      {
        accessorKey: "taskId",
        header: "Task",
        cell: ({ row }) => (
          <div>
            <Link to={`/app/review/${row.original.id}`} className="font-semibold text-primary hover:underline">
              {row.original.taskId}
            </Link>
            <p className="text-xs text-slate-500">{row.original.entry.entryId}</p>
          </div>
        ),
      },
      {
        id: "source",
        header: "Source",
        cell: ({ row }) => (
          <div className="max-w-[220px]">
            <p className="truncate font-medium">{row.original.entry.sourceFile}</p>
            <p className="truncate text-xs text-slate-500">{row.original.entry.sourceBatch}</p>
          </div>
        ),
      },
      {
        id: "description",
        header: "Description",
        cell: ({ row }) => (
          <div className="max-w-[260px]">
            <p className="truncate font-medium">{row.original.entry.englishDescription}</p>
            <p className="truncate text-xs text-slate-500">{row.original.entry.originalDescription}</p>
          </div>
        ),
      },
      {
        id: "amount",
        header: "Amount",
        cell: ({ row }) => <span className="font-semibold tabular">{formatCurrency(row.original.entry.amount, row.original.entry.currency)}</span>,
      },
      { id: "category", header: "Category", cell: ({ row }) => <CategoryBadge category={row.original.entry.category} /> },
      { id: "status", header: "Review status", cell: ({ row }) => <ReviewStatusBadge status={row.original.status} /> },
      {
        id: "confidence",
        header: "Confidence",
        cell: ({ row }) => <div className="w-32"><ConfidenceBar label="Overall" value={row.original.entry.confidence?.overall ?? 0} compact /></div>,
      },
      {
        id: "validation",
        header: "Validation",
        cell: ({ row }) => {
          const errors = row.original.entry.issues.filter((issue) => issue.severity === "error").length;
          return <Badge variant={errors ? "danger" : row.original.entry.issues.length ? "warning" : "success"}>{errors ? `${errors} error(s)` : row.original.entry.issues.length ? `${row.original.entry.issues.length} warning(s)` : "Valid"}</Badge>;
        },
      },
      {
        accessorKey: "assignedReviewer",
        header: "Reviewer",
        cell: ({ row }) => <div><p className="font-medium">{row.original.assignedReviewer}</p><p className="text-xs text-slate-500">{row.original.reviewerGroup}</p></div>,
      },
      {
        accessorKey: "priority",
        header: "Priority",
        cell: ({ row }) => <Badge variant={row.original.priority === "critical" ? "danger" : row.original.priority === "high" ? "warning" : "neutral"}>{row.original.priority}</Badge>,
      },
      { id: "updatedAt", header: "Updated", cell: ({ row }) => <span className="text-xs text-slate-500">{formatDateTime(row.original.updatedAt)}</span> },
      { id: "actions", header: "Actions", cell: ({ row }) => <Button asChild size="sm"><Link to={`/app/review/${row.original.id}`}>Open review</Link></Button> },
    ],
    [selectedIds, visibleTasks],
  );

  const canAssign = hasPermission(permissions.reviewAssign);
  const canApprove = hasPermission(permissions.reviewApprove);
  const canRequestChanges = hasPermission(permissions.reviewRequestChanges);
  const canExport = hasPermission(permissions.reviewExport);

  const dialogTitle =
    dialogAction === "assign"
      ? "Assign selected review tasks"
      : dialogAction === "approve"
        ? "Approve selected review tasks"
        : dialogAction === "reject"
          ? "Reject selected review tasks"
          : "Request corrections";

  return (
    <>
      <PageHeader
        eyebrow="Human review"
        title="Review queue"
        description="Filter, assign, validate, approve, reject, request corrections, and export human review tasks before posting."
        actions={<Button asChild variant="outline"><Link to="/app/settings/approval-rules"><SlidersHorizontal className="h-4 w-4" />Queue rules</Link></Button>}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {statusFilters.slice(1, 9).map((item) => (
          <button
            type="button"
            key={item.value}
            onClick={() => setStatusFilter(item.value)}
            className="rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:border-primary/50 dark:border-slate-800 dark:bg-slate-950"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-bold">{statusCounts[item.value] ?? 0}</p>
          </button>
        ))}
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-primary" />Queue filters and bulk actions</CardTitle>
          <CardDescription>Actions are enabled only when the signed-in role has the required review permission.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="w-full xl:max-w-sm">
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StatusFilter)}>
              <SelectTrigger><SelectValue placeholder="Filter review status" /></SelectTrigger>
              <SelectContent>
                {statusFilters.map((item) => <SelectItem key={item.value} value={item.value}>{item.label} ({statusCounts[item.value] ?? 0})</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled={!selectedIds.length || !canAssign} onClick={() => setDialogAction("assign")}><UserPlus className="h-4 w-4" />Assign reviewer</Button>
            <Button variant="success" disabled={!selectedIds.length || !canApprove} onClick={() => setDialogAction("approve")}><CheckCircle2 className="h-4 w-4" />Approve selected</Button>
            <Button variant="destructive" disabled={!selectedIds.length || !canApprove} onClick={() => setDialogAction("reject")}><XCircle className="h-4 w-4" />Reject selected</Button>
            <Button variant="outline" disabled={!selectedIds.length || !canRequestChanges} onClick={() => setDialogAction("request_correction")}><MessageSquareWarning className="h-4 w-4" />Request correction</Button>
            <Button variant="outline" disabled={!selectedIds.length || !canExport || bulkMutation.isPending} onClick={() => submitAction("export")}><Download className="h-4 w-4" />Export selected</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Review tasks</CardTitle>
          <CardDescription>{selectedIds.length} selected · {visibleTasks.length} visible · {tasks.length} total</CardDescription>
        </CardHeader>
        <CardContent>
          {tasksQuery.isLoading ? <LoadingState /> : tasksQuery.isError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{tasksQuery.error instanceof Error ? tasksQuery.error.message : "Unable to load review tasks."}</div>
          ) : visibleTasks.length === 0 ? (
            <EmptyState
              title={tasks.length === 0 ? "No review tasks yet" : "No tasks match this filter"}
              description={tasks.length === 0 ? "Upload and process a document. A company-scoped review task is created after extraction, classification, and validation." : "Choose another review status to see available tasks."}
              action={tasks.length === 0 ? <Button asChild><Link to="/app/files">Open files</Link></Button> : undefined}
            />
          ) : (
            <DataTable data={visibleTasks} columns={columns} searchPlaceholder="Search task, entry, file, description, reviewer, or SAP T-Code..." dense />
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogAction !== null} onOpenChange={(open) => !open && setDialogAction(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogTitle}</DialogTitle>
            <DialogDescription>{selectedIds.length} selected task(s). The decision will be written to approval history.</DialogDescription>
          </DialogHeader>

          {dialogAction === "assign" ? (
            <Select value={selectedReviewer} onValueChange={setSelectedReviewer}>
              <SelectTrigger><SelectValue placeholder="Select reviewer" /></SelectTrigger>
              <SelectContent>
                {reviewerOptions.map((reviewer) => <SelectItem key={reviewer.id} value={reviewer.id}>{reviewer.name} · {reviewer.role}</SelectItem>)}
              </SelectContent>
            </Select>
          ) : null}

          <Textarea
            value={comments}
            onChange={(event) => setComments(event.target.value)}
            placeholder={dialogAction === "reject" ? "Rejection reason (required)" : dialogAction === "request_correction" ? "Correction instructions (required)" : "Decision comments (optional)"}
            className="min-h-28"
          />

          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button
              variant={dialogAction === "reject" ? "destructive" : dialogAction === "approve" ? "success" : "default"}
              disabled={
                bulkMutation.isPending ||
                (dialogAction === "assign" && !selectedReviewer) ||
                ((dialogAction === "reject" || dialogAction === "request_correction") && !comments.trim())
              }
              onClick={() => dialogAction && submitAction(dialogAction)}
            >
              {bulkMutation.isPending ? "Processing..." : "Confirm action"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
