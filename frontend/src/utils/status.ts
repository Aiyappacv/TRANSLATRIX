export type OperationalStatus = "uploaded" | "processing" | "needs_review" | "in_review" | "reviewed" | "changes_requested" | "rejected" | "validation_failed" | "approved" | "sap_posted" | "sap_failed" | "completed" | "draft";

export const statusLabels: Record<OperationalStatus, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  needs_review: "Needs review",
  in_review: "In review",
  reviewed: "Reviewed",
  changes_requested: "Correction requested",
  rejected: "Rejected",
  validation_failed: "Validation failed",
  approved: "Approved",
  sap_posted: "SAP posted",
  sap_failed: "SAP failed",
  completed: "Completed",
  draft: "Draft",
};

export const statusTone: Record<OperationalStatus, "neutral" | "info" | "warning" | "danger" | "success"> = {
  uploaded: "neutral",
  processing: "info",
  needs_review: "warning",
  in_review: "info",
  reviewed: "info",
  changes_requested: "warning",
  rejected: "danger",
  validation_failed: "danger",
  approved: "success",
  sap_posted: "success",
  sap_failed: "danger",
  completed: "success",
  draft: "neutral",
};
