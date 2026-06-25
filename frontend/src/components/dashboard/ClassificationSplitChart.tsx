import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ClassificationSplit } from "@/types";

export function ClassificationSplitChart({ data }: { data: ClassificationSplit[] }) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="category" outerRadius={110} innerRadius={68} paddingAngle={3} label />
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
