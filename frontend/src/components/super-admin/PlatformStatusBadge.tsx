import { Badge } from "@/components/ui/badge";

const toneByStatus = {
  active: "success",
  operational: "success",
  healthy: "success",
  paid: "success",
  resolved: "success",
  current: "success",
  success: "success",
  trial: "warning",
  pending: "warning",
  degraded: "warning",
  delayed: "warning",
  maintenance: "warning",
  not_configured: "neutral",
  unknown: "neutral",
  open: "warning",
  investigating: "warning",
  waiting_customer: "warning",
  past_due: "danger",
  suspended: "danger",
  outage: "danger",
  blocked: "danger",
  critical: "danger",
  high: "danger",
  failed: "danger",
  denied: "danger",
  in_progress: "info",
  new: "info",
  medium: "info",
  normal: "info",
  low: "neutral",
} as const;

export function PlatformStatusBadge({ status }: { status: string }) {
  const tone = toneByStatus[status as keyof typeof toneByStatus] ?? "neutral";
  return <Badge variant={tone}>{status.replaceAll("_", " ")}</Badge>;
}
