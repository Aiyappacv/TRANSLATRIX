import type { SapPostingStatus } from "@/types";
import { Badge } from "@/components/ui/badge";

const tone: Record<SapPostingStatus, "success" | "info" | "warning" | "danger" | "neutral"> = {
  ready: "info",
  queued: "warning",
  posting: "warning",
  posted: "success",
  failed: "danger",
  reversed: "neutral",
};

export function SapPostingStatusBadge({ status }: { status: SapPostingStatus }) {
  return <Badge variant={tone[status]}>{status.replaceAll("_", " ")}</Badge>;
}
