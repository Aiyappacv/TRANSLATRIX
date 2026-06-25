import type { IntegrationStatus } from "@/types";
import { Badge } from "@/components/ui/badge";

const tone: Record<IntegrationStatus, "success" | "info" | "warning" | "danger" | "neutral"> = {
  connected: "success",
  available: "neutral",
  degraded: "warning",
  disabled: "neutral",
  syncing: "info",
  error: "danger",
};

export function IntegrationStatusBadge({ status }: { status: IntegrationStatus }) {
  return <Badge variant={tone[status]}>{status.replaceAll("_", " ")}</Badge>;
}
