import type { FinancialEntry } from "./financialEntry";

export type ReviewTaskStatus =
  | "pending_review"
  | "in_review"
  | "validation_failed"
  | "low_confidence"
  | "ready_for_approval"
  | "approved"
  | "rejected"
  | "sap_failed"
  | "changes_requested"
  | "second_approval";

export type ReviewPriority = "low" | "medium" | "high" | "critical";

export type ReviewDecisionType =
  | "task_created"
  | "assigned"
  | "review_started"
  | "field_changed"
  | "checklist_updated"
  | "comment_added"
  | "approved"
  | "rejected"
  | "changes_requested"
  | "second_approval_requested"
  | "exported"
  | "sap_failed";

export type ReviewBulkAction =
  | "assign"
  | "approve"
  | "reject"
  | "request_correction"
  | "export";

export interface ReviewActor {
  id: string;
  name: string;
  role: string;
}

export interface ApprovalChecklistItem {
  id: string;
  label: string;
  checked: boolean;
  required: boolean;
}

export interface ReviewTask {
  id: string;
  taskId: string;
  entry: FinancialEntry;
  status: ReviewTaskStatus;
  assignedReviewer: string;
  assignedReviewerId?: string;
  reviewerGroup: string;
  priority: ReviewPriority;
  dueAt: string;
  reviewerComments: string;
  checklist: ApprovalChecklistItem[];
  secondApprovalRequired: boolean;
  secondApprovalReason?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApprovalHistoryEvent {
  id: string;
  taskId: string;
  entryId: string;
  actorId: string;
  actor: string;
  actorRole: string;
  decision: ReviewDecisionType;
  field?: string;
  oldValue?: string;
  newValue?: string;
  comments?: string;
  timestamp: string;
}

export interface SaveReviewInput {
  accountingEntry: FinancialEntry["accountingEntry"];
  checklist: ApprovalChecklistItem[];
  reviewerComments: string;
}

export interface ReviewBulkActionInput {
  taskIds: string[];
  action: ReviewBulkAction;
  actor: ReviewActor;
  reviewerId?: string;
  reviewerName?: string;
  comments?: string;
}

export interface ReviewBulkActionResult {
  action: ReviewBulkAction;
  succeeded: string[];
  failed: Array<{ taskId: string; reason: string }>;
}
