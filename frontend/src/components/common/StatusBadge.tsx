import { Badge } from "@/components/ui/badge";
import { statusLabels, statusTone, type OperationalStatus } from "@/utils/status";

export function StatusBadge({ status }: { status: OperationalStatus | string }) {
  const typed = status as OperationalStatus;
  return <Badge variant={statusTone[typed] ?? "neutral"}>{statusLabels[typed] ?? status.replaceAll("_", " ")}</Badge>;
}
