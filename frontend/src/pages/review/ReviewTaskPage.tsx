import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  History,
  MessageSquareWarning,
  Save,
  ShieldAlert,
  UserCheck,
  XCircle,
} from "lucide-react";
import type { ApprovalChecklistItem, FinancialEntry, ReviewActor, ReviewBulkActionResult } from "@/types";
import { reviewApi } from "@/services/reviewApi";
import { sapApi } from "@/services/sapApi";
import { fileApi } from "@/services/fileApi";
import { useAuthStore } from "@/store/authStore";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { OriginalFilePreview } from "@/components/files/OriginalFilePreview";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { CategoryBadge } from "@/components/common/CategoryBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { JsonPayloadEditor } from "@/components/common/JsonPayloadEditor";
import { ApprovalChecklist } from "@/components/review/ApprovalChecklist";
import { ReviewAccountingEditor } from "@/components/review/ReviewAccountingEditor";
import { ReviewStatusBadge } from "@/components/review/ReviewStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { usePermissions } from "@/hooks/usePermissions";
import { useToast } from "@/hooks/useToast";
import { permissions, roleLabels } from "@/utils/permissions";
import { formatCurrency, formatDateTime } from "@/utils/formatters";

type DecisionAction = "approve" | "reject" | "request_changes" | "second_approval" | null;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function ensureActionSucceeded(result: ReviewBulkActionResult) {
  if (result.failed.length) throw new Error(result.failed.map((item) => item.reason).join(" "));
  return result;
}

export function ReviewTaskDetailPage() {
  const { taskId = "review_entry_001" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const user = useAuthStore((state) => state.user);
  const { hasPermission } = usePermissions();
  const startedTaskRef = useRef<string | null>(null);
  const canEdit = hasPermission(permissions.reviewEdit);
  const canApprove = hasPermission(permissions.reviewApprove);
  const canRequestChanges = hasPermission(permissions.reviewRequestChanges);
  const canSecondApprove = hasPermission(permissions.reviewSecondApprove);

  const [accountingEntry, setAccountingEntry] = useState<FinancialEntry["accountingEntry"] | null>(null);
  const [checklist, setChecklist] = useState<ApprovalChecklistItem[]>([]);
  const [reviewerComments, setReviewerComments] = useState("");
  const [decisionAction, setDecisionAction] = useState<DecisionAction>(null);
  const [decisionComments, setDecisionComments] = useState("");

  const taskQuery = useQuery({ queryKey: ["review-task", taskId], queryFn: () => reviewApi.getTask(taskId) });
  const sourceFileQuery = useQuery({ queryKey: ["review-source-file", taskQuery.data?.entry.fileId], queryFn: () => fileApi.getFile(taskQuery.data!.entry.fileId), enabled: Boolean(taskQuery.data?.entry.fileId) });
  const payloadQuery = useQuery({
    queryKey: ["sap-payload", taskQuery.data?.entry.id],
    queryFn: () => sapApi.getPayload(taskQuery.data!.entry.id),
    enabled: Boolean(taskQuery.data?.entry.id),
  });

  const actor: ReviewActor = {
    id: user?.id ?? "anonymous",
    name: user?.name ?? "Unknown user",
    role: user?.roles[0] ? (roleLabels[user.roles[0]] ?? user.roles[0]) : "Unknown role",
  };

  useEffect(() => {
    if (!taskQuery.data) return;
    setAccountingEntry(clone(taskQuery.data.entry.accountingEntry));
    setChecklist(clone(taskQuery.data.checklist));
    setReviewerComments(taskQuery.data.reviewerComments);
  }, [taskQuery.data]);

  const startReviewMutation = useMutation({
    mutationFn: () => reviewApi.startReview(taskId, actor),
    onSuccess: (task) => queryClient.setQueryData(["review-task", taskId], task),
  });

  const startReview = startReviewMutation.mutate;

  useEffect(() => {
    const task = taskQuery.data;
    if (!task || startedTaskRef.current === task.id) return;
    startedTaskRef.current = task.id;
    if (canEdit && (task.status === "pending_review" || task.status === "ready_for_approval")) startReview();
  }, [canEdit, startReview, taskQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!taskQuery.data || !accountingEntry) throw new Error("Review task is not ready.");
      return reviewApi.saveReview(taskQuery.data.id, { accountingEntry, checklist, reviewerComments }, actor);
    },
    onSuccess: async (task) => {
      queryClient.setQueryData(["review-task", taskId], task);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["approval-history"] }),
      ]);
      toast.success("Review changes saved", "Accounting edits, checklist evidence, and comments were recorded.");
    },
    onError: (error) => toast.error("Unable to save review", error instanceof Error ? error.message : "Unknown error"),
  });

  const decisionMutation = useMutation({
    mutationFn: async ({ action, comments }: { action: Exclude<DecisionAction, null>; comments: string }) => {
      const task = taskQuery.data;
      if (!task || !accountingEntry) throw new Error("Review task is not ready.");

      await reviewApi.saveReview(task.id, { accountingEntry, checklist, reviewerComments }, actor);

      if (action === "approve") return ensureActionSucceeded(await reviewApi.approve(task.id, actor, comments));
      if (action === "reject") return ensureActionSucceeded(await reviewApi.reject(task.id, actor, comments));
      if (action === "request_changes") return ensureActionSucceeded(await reviewApi.requestChanges(task.id, actor, comments));
      return reviewApi.sendForSecondApproval(task.id, actor, comments);
    },
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["review-task", taskId] }),
        queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["approval-history"] }),
      ]);
      const message =
        variables.action === "approve"
          ? "Entry approved"
          : variables.action === "reject"
            ? "Entry rejected"
            : variables.action === "request_changes"
              ? "Changes requested"
              : "Second approval requested";
      toast.success(message, "The decision and its comments were written to approval history.");
      setDecisionAction(null);
      setDecisionComments("");
    },
    onError: (error) => toast.error("Decision could not be completed", error instanceof Error ? error.message : "Unknown error"),
  });

  const completeReviewMutation = useMutation({
    mutationFn: async () => {
      const task = taskQuery.data;
      if (!task || !accountingEntry) throw new Error("Review task is not ready.");
      await reviewApi.saveReview(task.id, { accountingEntry, checklist, reviewerComments }, actor);
      return ensureActionSucceeded(await reviewApi.markReviewed(task.id, actor, reviewerComments.trim() || undefined));
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["review-task", taskId] }),
        queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["approval-history"] }),
      ]);
      toast.success("Review completed", "The task was sent to the approver without granting final approval.");
    },
    onError: (error) => toast.error("Review could not be completed", error instanceof Error ? error.message : "Unknown error"),
  });

  const task = taskQuery.data;
  const entry = task?.entry;

  const totals = useMemo(() => {
    if (!accountingEntry) return { debit: 0, credit: 0, balanced: false };
    const debit = accountingEntry.debitLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
    const credit = accountingEntry.creditLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
    return { debit, credit, balanced: Math.abs(debit - credit) < 0.01 };
  }, [accountingEntry]);

  const requiredChecklistComplete = checklist.filter((item) => item.required).every((item) => item.checked);
  const blockingErrors = entry?.issues.filter((issue) => issue.severity === "error") ?? [];

  const approvalBlockedReason = !requiredChecklistComplete
    ? "Complete all required checklist items."
    : !totals.balanced
      ? "Balance debit and credit totals."
      : blockingErrors.length
        ? "Resolve blocking validation errors."
        : task?.secondApprovalRequired && task.status !== "second_approval"
          ? "Send this high-value task for second approval first."
          : null;

  if (taskQuery.isError) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{taskQuery.error instanceof Error ? taskQuery.error.message : "Unable to load the review task."}</div>;
  }

  if (taskQuery.isLoading || !task || !entry || !accountingEntry) return <LoadingState />;

  const dialogTitle =
    decisionAction === "approve"
      ? "Approve accounting entry"
      : decisionAction === "reject"
        ? "Reject accounting entry"
        : decisionAction === "request_changes"
          ? "Request changes"
          : "Send for second approval";

  const submitDecision = () => {
    if (!decisionAction) return;
    decisionMutation.mutate({ action: decisionAction, comments: decisionComments.trim() || reviewerComments.trim() });
  };

  return (
    <>
      <PageHeader
        eyebrow="Human review task"
        title={`${task.taskId} · ${entry.reference}`}
        badge={entry.sapTCode}
        description="Source evidence, extracted data, editable accounting lines, validation, approval checklist, and RBAC-aware decisions."
        actions={<Button asChild variant="outline"><Link to="/app/review/history"><History className="h-4 w-4" />Approval history</Link></Button>}
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr_0.95fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-primary" />Source document preview</CardTitle>
              <CardDescription>Original evidence and exact source location used by OCR and extraction.</CardDescription>
            </CardHeader>
            <CardContent>
              {sourceFileQuery.isLoading ? <LoadingState label="Loading source preview" /> : sourceFileQuery.data ? <OriginalFilePreview file={sourceFileQuery.data} /> : <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Source preview is unavailable. Open the source file record for details.</div>}
              <div className="mt-4 rounded-xl border border-slate-200 p-4 text-sm dark:border-slate-800">
                <p className="font-semibold">{entry.sourceFile}</p>
                <p className="mt-1 text-slate-500">Batch {entry.sourceBatch} · Page {entry.sourcePage ?? "N/A"} · Row {entry.sourceRow ?? "N/A"}</p>
                <Button asChild variant="outline" size="sm" className="mt-3"><Link to={`/app/files/${entry.fileId}`}>Open source file</Link></Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary" />Extracted data</CardTitle>
              <CardDescription>Compare source text, extracted values, category, and SAP mapping.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Original description</p>
                <p className="mt-2 text-sm">{entry.originalDescription}</p>
              </div>

              <div className="grid gap-3 rounded-xl bg-slate-50 p-4 dark:bg-slate-900 sm:grid-cols-2">
                <div><p className="text-xs text-slate-500">Amount</p><p className="font-bold tabular">{formatCurrency(entry.amount, entry.currency)}</p></div>
                <div><p className="text-xs text-slate-500">Vendor/customer</p><p className="font-semibold">{entry.vendor ?? entry.customer ?? "Not extracted"}</p></div>
                <div><p className="text-xs text-slate-500">Category</p><CategoryBadge category={entry.category} /></div>
                <div><p className="text-xs text-slate-500">Entry status</p><StatusBadge status={entry.status} /></div>
                <div><p className="text-xs text-slate-500">Invoice/reference</p><p className="font-semibold">{entry.invoiceNumber ?? entry.referenceNumber}</p></div>
                <div><p className="text-xs text-slate-500">Date</p><p className="font-semibold">{entry.date || "Not extracted"}</p></div>
                <div><p className="text-xs text-slate-500">GST/VAT</p><p className="font-semibold">{entry.gstVatNumber || "Not extracted"}</p></div>
                <div><p className="text-xs text-slate-500">Tax amount</p><p className="font-semibold">{entry.taxAmount != null ? formatCurrency(entry.taxAmount, entry.currency) : "Not extracted"}</p></div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <ConfidenceBar label="OCR" value={entry.confidence?.ocr ?? 0} />
                <ConfidenceBar label="Classification" value={entry.confidence?.classification ?? 0} />
                <ConfidenceBar label="SAP mapping" value={entry.confidence?.mapping ?? 0} />
              </div>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
                <p className="text-sm font-semibold">Classification and SAP mapping</p>
                <p className="mt-2 text-sm text-slate-500">{entry.classificationReason}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge variant="brand">{entry.sapTCode}</Badge>
                  <Badge>{entry.postingProcess}</Badge>
                  <Badge>{entry.glSuggestion}</Badge>
                  <Badge>{entry.taxCode ?? "No tax code"}</Badge>
                  <Badge>{entry.costCenter ?? "No cost center"}</Badge>
                </div>
              </div>

              {payloadQuery.data ? <JsonPayloadEditor title="SAP/accounting payload" value={payloadQuery.data} height={320} /> : null}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><ClipboardCheck className="h-5 w-5 text-primary" />Approval panel</CardTitle>
              <CardDescription>Only roles with the required permissions can edit or execute decisions.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><p className="text-xs text-slate-500">Current status</p><div className="mt-2"><ReviewStatusBadge status={task.status} /></div></div>
                <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><p className="text-xs text-slate-500">Assigned reviewer</p><p className="mt-2 font-semibold">{task.assignedReviewer}</p></div>
                <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><p className="text-xs text-slate-500">Priority</p><Badge className="mt-2" variant={task.priority === "critical" ? "danger" : task.priority === "high" ? "warning" : "neutral"}>{task.priority}</Badge></div>
                <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800"><p className="text-xs text-slate-500">Last updated</p><p className="mt-2 text-sm font-medium">{formatDateTime(task.updatedAt)}</p></div>
              </div>

              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                <p className="text-sm font-semibold">Confidence summary</p>
                <div className="mt-3"><ConfidenceBar label="Overall" value={entry.confidence?.overall ?? 0} /></div>
              </div>

              <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                <p className="mb-3 text-sm font-semibold">Validation errors</p>
                {entry.issues.length ? (
                  <div className="space-y-2">
                    {entry.issues.map((issue) => (
                      <div key={issue.code} className={`rounded-lg border p-3 text-sm ${issue.severity === "error" ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"}`}>
                        <Badge variant={issue.severity === "error" ? "danger" : "warning"}>{issue.code}</Badge>
                        <p className="mt-2">{issue.message}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">No blocking validation errors.</p>}
              </div>

              <ReviewAccountingEditor value={accountingEntry} currency={entry.currency} disabled={!canEdit} onChange={setAccountingEntry} />

              {task.secondApprovalRequired ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                  <div className="flex items-center gap-2 font-semibold"><UserCheck className="h-4 w-4" />Second approval required</div>
                  <p className="mt-1">{task.secondApprovalReason}</p>
                </div>
              ) : null}

              <ApprovalChecklist items={checklist} disabled={!canEdit} onChange={setChecklist} />

              <div>
                <p className="mb-2 text-sm font-semibold">Reviewer comments</p>
                <Textarea value={reviewerComments} disabled={!canEdit} onChange={(event) => setReviewerComments(event.target.value)} placeholder="Add approval evidence, correction details, master-data confirmation, or SAP posting notes..." className="min-h-28" />
              </div>

              <Button className="w-full" variant="outline" disabled={!canEdit || saveMutation.isPending} onClick={() => saveMutation.mutate()}>
                <Save className="h-4 w-4" />{saveMutation.isPending ? "Saving..." : "Save review changes"}
              </Button>

              {approvalBlockedReason ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"><ShieldAlert className="mr-2 inline h-4 w-4" />{approvalBlockedReason}</div> : null}

              {!canEdit && !canApprove && !canRequestChanges ? <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">Your current role has read-only access to this review task.</div> : null}
            </CardContent>
          </Card>

          <div className="sticky bottom-0 z-10 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-enterprise backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {canEdit && !canApprove ? <Button variant="success" disabled={!requiredChecklistComplete || !totals.balanced || blockingErrors.length > 0 || completeReviewMutation.isPending} onClick={() => completeReviewMutation.mutate()}><CheckCircle2 className="h-4 w-4" />Complete review / Send to approver</Button> : null}
              {canApprove ? <Button variant="success" disabled={Boolean(approvalBlockedReason) || decisionMutation.isPending} onClick={() => setDecisionAction("approve")}><CheckCircle2 className="h-4 w-4" />Approve</Button> : null}
              <Button variant="destructive" disabled={!canEdit || decisionMutation.isPending} onClick={() => setDecisionAction("reject")}><XCircle className="h-4 w-4" />Reject</Button>
              <Button variant="outline" disabled={!canRequestChanges || decisionMutation.isPending} onClick={() => setDecisionAction("request_changes")}><MessageSquareWarning className="h-4 w-4" />Request changes</Button>
              <Button disabled={!canSecondApprove || !requiredChecklistComplete || !totals.balanced || decisionMutation.isPending} onClick={() => setDecisionAction("second_approval")}><UserCheck className="h-4 w-4" />Send for second approval</Button>
            </div>
          </div>
        </div>
      </div>

      <Dialog open={decisionAction !== null} onOpenChange={(open) => !open && setDecisionAction(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogTitle}</DialogTitle>
            <DialogDescription>The decision, actor, old/new status, timestamp, and comments will be retained in approval history.</DialogDescription>
          </DialogHeader>
          <Textarea
            value={decisionComments}
            onChange={(event) => setDecisionComments(event.target.value)}
            className="min-h-28"
            placeholder={decisionAction === "reject" ? "Rejection reason (required)" : decisionAction === "request_changes" ? "Required changes and correction instructions" : "Decision comments"}
          />
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button
              variant={decisionAction === "reject" ? "destructive" : decisionAction === "approve" ? "success" : "default"}
              disabled={decisionMutation.isPending || ((decisionAction === "reject" || decisionAction === "request_changes") && !decisionComments.trim() && !reviewerComments.trim())}
              onClick={submitDecision}
            >
              {decisionMutation.isPending ? "Processing..." : "Confirm decision"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export { ReviewTaskDetailPage as ReviewTaskPage };
