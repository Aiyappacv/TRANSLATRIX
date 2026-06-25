import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PlatformUsagePoint } from "@/types";

export function PlatformUsageChart({ data }: { data: PlatformUsagePoint[] }) {
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 4, right: 16, top: 12, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} />
          <YAxis tickLine={false} axisLine={false} fontSize={12} />
          <Tooltip contentStyle={{ borderRadius: 12 }} />
          <Legend />
          <Line type="monotone" dataKey="files" name="Files" stroke="currentColor" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="entries" name="Entries" stroke="currentColor" strokeWidth={2} strokeDasharray="5 3" dot={false} />
          <Line type="monotone" dataKey="postings" name="Postings" stroke="currentColor" strokeWidth={2} strokeDasharray="2 3" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
