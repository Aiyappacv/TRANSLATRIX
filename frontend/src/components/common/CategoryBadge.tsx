import { Badge } from "@/components/ui/badge";
import type { FinancialCategory } from "@/types";

const categoryTone: Record<FinancialCategory, "danger" | "success" | "info" | "warning"> = {
  Expenses: "danger",
  Income: "success",
  Assets: "info",
  Liabilities: "warning",
};

export function CategoryBadge({ category }: { category: FinancialCategory }) {
  return <Badge variant={categoryTone[category]}>{category}</Badge>;
}
