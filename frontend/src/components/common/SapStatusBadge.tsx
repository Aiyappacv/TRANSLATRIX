import { Badge } from "@/components/ui/badge";

export function SapStatusBadge({ status }: { status: string }) {
  const variant = status.includes("posted") || status.includes("success") ? "success" : status.includes("failed") ? "danger" : "warning";
  return <Badge variant={variant}>{status.replaceAll("_", " ")}</Badge>;
}
