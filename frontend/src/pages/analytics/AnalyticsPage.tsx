import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { monitoringApi } from "@/services/monitoringApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function Breakdown({ title, description, data }: { title: string; description: string; data: Array<{ label: string; value: number }> }) {
  return <Card><CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader><CardContent><div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 20 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis dataKey="label" type="category" width={130} /><Tooltip /><Bar dataKey="value" fill="#4f46e5" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></div></CardContent></Card>;
}

export function AnalyticsPage() {
  const query = useQuery({ queryKey: ["monitoring", "analytics"], queryFn: monitoringApi.getAnalytics });
  if (query.isLoading) return <LoadingState label="Loading enterprise analytics..." />;
  if (query.isError || !query.data) return <ErrorState title="Analytics unavailable" description="Enterprise monitoring metrics could not be loaded." onRetry={() => query.refetch()} />;
  const data = query.data;
  return <div className="space-y-6"><PageHeader eyebrow="Phase 13 · Monitoring" title="Analytics" description="Executive processing, confidence, approval, validation, client, file-type, and SAP posting analytics." />
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{data.metrics.map((metric) => <MetricCard key={metric.key} label={metric.label} value={metric.value} delta={metric.delta} tone={metric.tone} />)}</div>
    <div className="grid gap-6 xl:grid-cols-2"><Card><CardHeader><CardTitle>Processing volume</CardTitle><CardDescription>Files and extracted entries by day.</CardDescription></CardHeader><CardContent><div className="h-80"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="period" /><YAxis /><Tooltip /><Legend /><Bar dataKey="files" fill="#4f46e5" radius={[5, 5, 0, 0]} /><Bar dataKey="entries" fill="#0ea5e9" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></CardContent></Card>
      <Card><CardHeader><CardTitle>Confidence trends</CardTitle><CardDescription>OCR, translation, and classification confidence.</CardDescription></CardHeader><CardContent><div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="period" /><YAxis domain={[85, 100]} /><Tooltip /><Legend /><Line type="monotone" dataKey="ocrConfidence" stroke="#4f46e5" strokeWidth={2} /><Line type="monotone" dataKey="translationConfidence" stroke="#0ea5e9" strokeWidth={2} /><Line type="monotone" dataKey="classificationConfidence" stroke="#10b981" strokeWidth={2} /></LineChart></ResponsiveContainer></div></CardContent></Card></div>
    <div className="grid gap-6 xl:grid-cols-2"><Card><CardHeader><CardTitle>SAP posting success/failure</CardTitle><CardDescription>Posting outcome rate and average approval time.</CardDescription></CardHeader><CardContent><div className="h-80"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="period" /><YAxis /><Tooltip /><Legend /><Line type="monotone" dataKey="sapSuccess" stroke="#10b981" strokeWidth={2} /><Line type="monotone" dataKey="sapFailure" stroke="#ef4444" strokeWidth={2} /><Line type="monotone" dataKey="approvalMinutes" stroke="#f59e0b" strokeWidth={2} /></LineChart></ResponsiveContainer></div></CardContent></Card><Breakdown title="Entries by category" description="Automated classification distribution." data={data.entriesByCategory} /></div>
    <div className="grid gap-6 xl:grid-cols-3"><Breakdown title="Validation error breakdown" description="Top validation failures and warnings." data={data.validationErrors} /><Breakdown title="Top clients by volume" description="Companies with the highest processed file volume." data={data.topClients} /><Breakdown title="Top failed file types" description="Document types causing the most processing failures." data={data.failedFileTypes} /></div>
  </div>;
}
