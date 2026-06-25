import { Badge } from "@/components/ui/badge";

export function ValidationSeverityBadge({ severity }: { severity: "error" | "warning" | "info" }) {
  return <Badge variant={severity === "error" ? "danger" : severity === "warning" ? "warning" : "info"}>{severity}</Badge>;
}
