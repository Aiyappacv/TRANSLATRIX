import { Badge } from "@/components/ui/badge";
import { formatPercent } from "@/utils/formatters";

export function ConfidenceBadge({ value }: { value: number }) {
  return <Badge variant={value >= 0.9 ? "success" : value >= 0.8 ? "warning" : "danger"}>{formatPercent(value)}</Badge>;
}
