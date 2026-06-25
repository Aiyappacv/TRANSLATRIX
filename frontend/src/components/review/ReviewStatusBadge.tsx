import type { ReviewTaskStatus } from "@/types";
import { Badge } from "@/components/ui/badge";

const labels: Record<ReviewTaskStatus, string> = {
  pending_review: "Pending review",
  in_review: "In review",
  validation_failed: "Validation failed",
  low_confidence: "Low confidence",
  ready_for_approval: "Ready for approval",
  approved: "Approved",
  rejected: "Rejected",
  sap_failed: "SAP failed",
  changes_requested: "Changes requested",
  second_approval: "Second approval",
};

export function ReviewStatusBadge({ status }: { status: ReviewTaskStatus }) {
  const variant =
    status === "approved"
      ? "success"
      : ["rejected", "sap_failed", "validation_failed"].includes(status)
        ? "danger"
        : ["low_confidence", "changes_requested", "second_approval"].includes(status)
          ? "warning"
          : status === "ready_for_approval"
            ? "success"
            : "brand";

  return <Badge variant={variant}>{labels[status]}</Badge>;
}
