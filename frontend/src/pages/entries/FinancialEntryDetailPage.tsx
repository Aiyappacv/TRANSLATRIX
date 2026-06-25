import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, FileText, RotateCcw, Save, ShieldCheck, XCircle } from "lucide-react";
import { toast } from "sonner";
import { entryApi } from "@/services/entryApi";
import { fileApi } from "@/services/fileApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { CategoryBadge } from "@/components/common/CategoryBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { OriginalFilePreview } from "@/components/files/OriginalFilePreview";
import { ClassificationConfidencePanel } from "@/components/entries/ClassificationConfidencePanel";
import { CategoryEditor } from "@/components/entries/CategoryEditor";
import { SapMappingEditor } from "@/components/entries/SapMappingEditor";
import { AccountingEntryEditor } from "@/components/entries/AccountingEntryEditor";
import { ValidationPanel } from "@/components/entries/ValidationPanel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { formatCurrency, formatDate } from "@/utils/formatters";
import { permissions } from "@/utils/permissions";
import { usePermissions } from "@/hooks/usePermissions";
import type { FinancialEntry } from "@/types";

export type EntryDraft = Pick<FinancialEntry,
  | "category"
  | "subcategory"
  | "date"
  | "amount"
  | "currency"
  | "vendor"
  | "customer"
  | "reference"
  | "invoiceNumber"
  | "sapTCode"
  | "operation"
  | "glAccount"
  | "taxCode"
  | "costCenter"
>;

type ActionKind = "reviewed" | "approved" | "rejected" | "changes_requested";

const actionCopy: Record<ActionKind, { title: string; description: string; button: string }> = {
  reviewed: { title: "Mark entry as reviewed?", description: "This records that the source, classification, and accounting entry were reviewed.", button: "Mark reviewed" },
  approved: { title: "Approve this financial entry?", description: "Approval is blocked unless current validation passes and the journal is balanced.", button: "Approve entry" },
  rejected: { title: "Reject this financial entry?", description: "Add a reason. The rejection will be persisted and recorded in Approval History.", button: "Reject entry" },
  changes_requested: { title: "Request a correction?", description: "Add clear correction instructions. The entry will return to the review queue.", button: "Request correction" },
};

function toDraft(item: FinancialEntry): EntryDraft {
  return {
    category: item.category,
    subcategory: item.subcategory,
    date: item.date,
    amount: item.amount,
    currency: item.currency,
    vendor: item.vendor,
    customer: item.customer,
    reference: item.reference || item.referenceNumber,
    invoiceNumber: item.invoiceNumber,
    sapTCode: item.sapTCode,
    operation: item.operation || item.postingProcess,
    glAccount: item.glAccount,
    taxCode: item.taxCode,
    costCenter: item.costCenter,
  };
}

export function FinancialEntryDetailPage() {
  const { entryId = "entry_001" } = useParams();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const entry = useQuery({ queryKey: ["entry", entryId], queryFn: () => entryApi.getEntry(entryId) });
  const file = useQuery({ queryKey: ["entry-file", entry.data?.fileId], queryFn: () => fileApi.getFile(entry.data!.fileId), enabled: Boolean(entry.data?.fileId) });
  const [draft, setDraft] = useState<EntryDraft | null>(null);
  const [accountingEntry, setAccountingEntry] = useState<FinancialEntry["accountingEntry"] | null>(null);
  const [localIssues, setLocalIssues] = useState<FinancialEntry["issues"]>([]);
  const [localValidation, setLocalValidation] = useState<FinancialEntry["validationStatus"]>("warning");
  const [action, setAction] = useState<ActionKind | null>(null);
  const [comment, setComment] = useState("");

  useEffect(() => {
    if (!entry.data) return;
    setDraft(toDraft(entry.data));
    setAccountingEntry(structuredClone(entry.data.accountingEntry));
    setLocalIssues(entry.data.issues);
    setLocalValidation(entry.data.validationStatus);
  }, [entry.data]);

  const candidate = useMemo(() => {
    if (!entry.data || !draft || !accountingEntry) return null;
    return {
      ...entry.data,
      ...draft,
      referenceNumber: draft.reference,
      postingProcess: draft.operation,
      glSuggestion: draft.glAccount,
      accountingEntry,
      issues: localIssues,
      validationStatus: localValidation,
    } satisfies FinancialEntry;
  }, [accountingEntry, draft, entry.data, localIssues, localValidation]);

  const save = useMutation({
    mutationFn: async () => {
      if (!candidate) throw new Error("Entry draft is not ready");
      return entryApi.updateEntry(entryId, candidate);
    },
    onSuccess: async (updated) => {
      queryClient.setQueryData(["entry", entryId], updated);
      await queryClient.invalidateQueries({ queryKey: ["entries"] });
      toast.success("Financial entry draft saved");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to save the financial entry"),
  });

  const validate = useMutation({
    mutationFn: async () => {
      if (!candidate) throw new Error("Entry draft is not ready");
      return entryApi.validateEntry(entryId, candidate);
    },
    onSuccess: (result) => {
      setLocalIssues(result.issues);
      setLocalValidation(result.validationStatus);
      toast[result.validationStatus === "valid" ? "success" : "warning"](result.validationStatus === "valid" ? "All validation rules passed" : "Validation found issues that need attention");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Validation failed to run"),
  });

  const invalidateWorkflow = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["entry", entryId] }),
      queryClient.invalidateQueries({ queryKey: ["entries"] }),
      queryClient.invalidateQueries({ queryKey: ["review-tasks"] }),
      queryClient.invalidateQueries({ queryKey: ["approval-history"] }),
      queryClient.invalidateQueries({ queryKey: ["sap-postings"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      queryClient.invalidateQueries({ queryKey: ["audit-logs"] }),
    ]);
  };

  const resubmit = useMutation({
    mutationFn: () => entryApi.resubmit(entryId, "Corrections completed and resubmitted for review."),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["entry", entryId], updated);
      await invalidateWorkflow();
      toast.success("Entry resubmitted for review");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to resubmit the corrected entry"),
  });

  const performAction = useMutation({
    mutationFn: async (kind: ActionKind) => {
      if ((kind === "rejected" || kind === "changes_requested") && !comment.trim()) throw new Error("A reason or correction comment is required");
      if (kind === "reviewed") return entryApi.markReviewed(entryId, comment.trim() || undefined);
      if (kind === "approved") return entryApi.approveEntry(entryId, comment.trim() || undefined);
      if (kind === "rejected") return entryApi.rejectEntry(entryId, comment.trim());
      return entryApi.requestCorrection(entryId, comment.trim());
    },
    onSuccess: async (updated, kind) => {
      queryClient.setQueryData(["entry", entryId], updated);
      await invalidateWorkflow();
      toast.success(kind === "approved" ? "Entry approved" : kind === "rejected" ? "Entry rejected" : kind === "changes_requested" ? "Correction requested" : "Entry marked as reviewed");
      setAction(null);
      setComment("");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to complete action"),
  });

  if (entry.isError) return <ErrorState description="Financial entry could not be loaded" onRetry={() => entry.refetch()} />;
  if (entry.isLoading || !entry.data || !draft || !accountingEntry || !candidate) return <LoadingState />;

  const item = candidate;
  const canEdit = hasPermission(permissions.entriesManage);
  const canReview = hasPermission(permissions.reviewEdit);
  const canApprove = hasPermission(permissions.reviewApprove);
  const canRequestChanges = hasPermission(permissions.reviewRequestChanges);
  const canResubmitCorrection = canEdit && item.status === "changes_requested" && !canReview && !canApprove;

  return (
    <>
      <PageHeader
        eyebrow="Financial entry detail"
        title={`${item.entryId} · ${item.originalDescription}`}
        badge={item.sapTCode}
        description={`${item.sourceFile} · ${formatDate(item.date)} · ${formatCurrency(item.amount, item.currency)} · Reviewer: ${item.reviewer ?? "Unassigned"}`}
        actions={
          <>
            <Button asChild variant="outline"><Link to="/app/entries">Back to entries</Link></Button>
            {canEdit ? <Button variant="outline" onClick={() => save.mutate()} disabled={save.isPending}><Save className="h-4 w-4" />{save.isPending ? "Saving..." : "Save draft"}</Button> : <Badge variant="neutral">Read-only access</Badge>}
            {canApprove ? <Button onClick={() => setAction("approved")}><CheckCircle2 className="h-4 w-4" />Approve</Button> : null}
          </>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr_0.95fr]">
        <div className="space-y-6">
          <Card><CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-primary" />Source file preview</CardTitle><CardDescription>Source page/row: {item.sourcePage ? `Page ${item.sourcePage}` : ""}{item.sourceRow ? ` Row ${item.sourceRow}` : ""}</CardDescription></CardHeader><CardContent>{file.isLoading ? <LoadingState /> : file.data ? <OriginalFilePreview file={file.data} /> : <p className="text-sm text-slate-500">Source file not available.</p>}</CardContent></Card>
          <ClassificationConfidencePanel entry={item} />
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-primary" />Source text and extracted values</CardTitle><CardDescription>Original source text, extracted values, and classification result.</CardDescription></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2"><p className="text-sm font-semibold">Original text</p><Textarea readOnly value={item.originalDescription} className="min-h-36 font-mono" /></div>
              <div className="grid gap-3 rounded-2xl bg-slate-50 p-4 dark:bg-slate-900 md:grid-cols-3"><div><p className="text-xs text-slate-500">Amount</p><p className="font-bold tabular">{formatCurrency(item.amount, item.currency)}</p></div><div><p className="text-xs text-slate-500">Party</p><p className="font-semibold">{item.vendor ?? item.customer ?? "Missing"}</p></div><div><p className="text-xs text-slate-500">Reference</p><p className="font-semibold">{item.reference}</p></div><div><p className="text-xs text-slate-500">Category</p><CategoryBadge category={item.category} /></div><div><p className="text-xs text-slate-500">Status</p><StatusBadge status={item.status} /></div><div><p className="text-xs text-slate-500">Validation</p><Badge variant={localValidation === "valid" ? "success" : localValidation === "failed" ? "danger" : "warning"}>{localValidation}</Badge></div></div>
              <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><p className="text-sm font-semibold">Classification result</p><p className="mt-2 text-sm text-slate-500">{item.classificationReason}</p></div>
            </CardContent>
          </Card>
          <div className={!canEdit ? "pointer-events-none opacity-80" : ""}>
            <CategoryEditor draft={draft} onChange={(patch) => { setDraft((current) => current ? { ...current, ...patch } : current); setLocalValidation("warning"); }} />
          </div>
          <div className={!canEdit ? "pointer-events-none opacity-80" : ""}>
            <AccountingEntryEditor value={accountingEntry} currency={draft.currency} issues={localIssues} onChange={(value) => { setAccountingEntry(value); setLocalValidation("warning"); }} />
          </div>
        </div>
        <div className="space-y-6">
          <div className={!canEdit ? "pointer-events-none opacity-80" : ""}><SapMappingEditor draft={draft} onChange={(patch) => { setDraft((current) => current ? { ...current, ...patch } : current); setLocalValidation("warning"); }} /></div>
          <div className={!canEdit ? "pointer-events-none opacity-80" : ""}><ValidationPanel entry={item} onRevalidate={() => validate.mutate()} revalidating={validate.isPending} /></div>
          <Card><CardHeader><CardTitle>Review actions</CardTitle><CardDescription>Actions are permission-aware and require confirmation before changing workflow state.</CardDescription></CardHeader><CardContent className="space-y-3">
            {canResubmitCorrection ? <Button className="w-full" onClick={() => resubmit.mutate()} disabled={resubmit.isPending || localValidation !== "valid"}><RotateCcw className="h-4 w-4" />{resubmit.isPending ? "Resubmitting..." : "Resubmit for review"}</Button> : null}
            {canResubmitCorrection && localValidation !== "valid" ? <p className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-sm text-warning">Resolve all blocking validation issues, save the entry, and revalidate it before resubmitting.</p> : null}
            <Button className="w-full" onClick={() => setAction("reviewed")} disabled={!canReview}><ShieldCheck className="h-4 w-4" />Mark reviewed</Button>
            <Button className="w-full" variant="success" onClick={() => setAction("approved")} disabled={!canApprove}><CheckCircle2 className="h-4 w-4" />Approve entry</Button>
            {canApprove && localValidation !== "valid" ? <div className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-sm text-warning"><div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4" /><span>Approval will be rejected by the backend until validation passes. Click Approve to see the exact blocking reason.</span></div></div> : null}
            <Button className="w-full" variant="outline" onClick={() => setAction("changes_requested")} disabled={!canRequestChanges}><AlertTriangle className="h-4 w-4" />Request correction</Button>
            <Button className="w-full" variant="destructive" onClick={() => setAction("rejected")} disabled={!canReview}><XCircle className="h-4 w-4" />Reject entry</Button>
          </CardContent></Card>
        </div>
      </div>

      <Dialog open={Boolean(action)} onOpenChange={(open) => { if (!open) { setAction(null); setComment(""); } }}>
        <DialogContent>
          {action ? (
            <>
              <DialogHeader><DialogTitle>{actionCopy[action].title}</DialogTitle><DialogDescription>{actionCopy[action].description}</DialogDescription></DialogHeader>
              {(action === "rejected" || action === "changes_requested") ? <div className="space-y-2"><Label htmlFor="correction-reason">Reason / comment</Label><Textarea id="correction-reason" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Describe the reason or correction required..." /></div> : null}
              <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setAction(null)}>Cancel</Button><Button variant={action === "rejected" ? "destructive" : action === "approved" ? "success" : "default"} onClick={() => performAction.mutate(action)} disabled={performAction.isPending}>{performAction.isPending ? "Working..." : actionCopy[action].button}</Button></div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
