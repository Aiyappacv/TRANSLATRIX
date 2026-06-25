import { Link } from "react-router-dom";
import {
  BadgeCheck,
  Ban,
  Bot,
  Cable,
  ChartNoAxesCombined,
  CircleX,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  CopyCheck,
  Database,
  DatabaseZap,
  FileText,
  Files,
  Gauge,
  History,
  IndianRupee,
  Layers3,
  Mail,
  PencilLine,
  Plug,
  RefreshCw,
  SearchCheck,
  Send,
  ShieldAlert,
  ShieldCheck,
  Table2,
  TimerOff,
  TimerReset,
  TriangleAlert,
  Unplug,
  Upload,
  UserCheck,
  Users,
  UsersRound,
  Webhook,
  BadgeHelp,
  BadgeX,
  type LucideIcon,
} from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { DashboardRecentEntry, DashboardStatusItem, DashboardTask, RoleDashboardDefinition, RoleDashboardKpi } from "@/types";
import { MetricCard } from "@/components/common/MetricCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const iconMap: Record<string, LucideIcon> = {
  BadgeCheck, Ban, Bot, Cable, ChartNoAxesCombined, CircleX, ClipboardCheck, ClipboardList, Clock3, CopyCheck,
  Database, DatabaseZap, Files, Gauge, History, IndianRupee, Layers3, Mail, PencilLine, Plug, RefreshCw,
  SearchCheck, Send, ShieldAlert, ShieldCheck, Table2, TimerOff, TimerReset, TriangleAlert, Unplug, Upload,
  UserCheck, Users, UsersRound, Webhook, BadgeHelp, BadgeX,
};

function statusVariant(tone: DashboardStatusItem["tone"]) {
  return tone === "danger" ? "danger" : tone === "warning" ? "warning" : tone === "success" ? "success" : tone === "info" ? "info" : "neutral";
}

export function DashboardKpiGrid({ kpis }: { kpis: RoleDashboardKpi[] }) {
  return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{kpis.map((item) => <MetricCard key={item.key} label={item.label} value={item.value} delta={item.delta} tone={item.tone} icon={iconMap[item.icon]} />)}</div>;
}

export function MyTasksCard({ tasks }: { tasks: DashboardTask[] }) {
  return <Card><CardHeader><CardTitle>My tasks</CardTitle><CardDescription>Prioritized work based on role, permissions, SLA, and risk.</CardDescription></CardHeader><CardContent className="space-y-3">{tasks.length ? tasks.map((task) => <Link key={task.id} to={task.href} className="block rounded-2xl border border-slate-200 p-4 transition hover:border-indigo-300 hover:bg-indigo-50/40 dark:border-slate-800 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/20"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{task.title}</p><p className="mt-1 text-sm text-slate-500">{task.description}</p></div><Badge variant={task.status === "attention" ? "warning" : task.status === "completed" ? "success" : "info"}>{task.dueLabel ?? task.status}</Badge></div></Link>) : <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">No action is assigned to this read-only role.</div>}</CardContent></Card>;
}

function StatusCard({ title, description, items }: { title: string; description: string; items: DashboardStatusItem[] }) {
  return <Card><CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader><CardContent className="space-y-3">{items.map((item) => <div key={item.label} className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 p-3 dark:border-slate-800"><div><p className="text-sm font-semibold">{item.label}</p><p className="mt-1 text-xs text-slate-500">{item.detail}</p></div><Badge variant={statusVariant(item.tone)}>{item.value}</Badge></div>)}</CardContent></Card>;
}

export function PendingReviewCard({ definition }: { definition: RoleDashboardDefinition }) {
  const pending = definition.kpis.find((item) => item.key === "pending" || item.key === "review" || item.key === "reviews");
  return <Card><CardHeader><CardTitle>Pending review</CardTitle><CardDescription>Human-in-the-loop work requiring attention.</CardDescription></CardHeader><CardContent><p className="text-4xl font-bold">{pending?.value ?? "0"}</p><p className="mt-2 text-sm text-slate-500">{pending?.delta ?? "Prioritized by confidence, value, and validation severity."}</p><Button asChild variant="outline" className="mt-5"><Link to="/app/review">Open review queue</Link></Button></CardContent></Card>;
}

export function ProcessingStatusCard({ items }: { items: DashboardStatusItem[] }) { return <StatusCard title="Processing status" description="OCR, translation, and classification health." items={items} />; }
export function SapPostingStatusCard({ items }: { items: DashboardStatusItem[] }) { return <StatusCard title="SAP posting status" description="Approved payloads, successes, and failures." items={items} />; }
export function ValidationIssuesCard({ items }: { items: DashboardStatusItem[] }) { return <StatusCard title="Validation issues" description="Blocking errors, warnings, and resolutions." items={items} />; }
export function IntegrationStatusCard({ items }: { items: DashboardStatusItem[] }) { return <StatusCard title="Integration status" description="Connector checks, synchronization, and degradation." items={items} />; }

export function RecentFilesCard({ files }: { files: RoleDashboardDefinition["recentFiles"] }) {
  return <Card><CardHeader><CardTitle>Recent files</CardTitle><CardDescription>Latest source documents in the active company.</CardDescription></CardHeader><CardContent className="space-y-3">{files.map((file) => <Link key={file.id} to={`/app/files/${file.id}`} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-900"><div className="rounded-xl bg-indigo-50 p-2 text-primary dark:bg-indigo-950/30"><FileText className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{file.name}</p><p className="text-xs text-slate-500">{file.createdAt}</p></div><Badge variant={file.status.includes("failed") ? "danger" : file.status.includes("Processing") ? "info" : "success"}>{file.status}</Badge></Link>)}</CardContent></Card>;
}

export function RecentEntriesTable({ entries }: { entries: DashboardRecentEntry[] }) {
  return <Card><CardHeader><CardTitle>Recent entries</CardTitle><CardDescription>Latest extracted and reviewed accounting entries.</CardDescription></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-xs uppercase tracking-wide text-slate-500"><tr><th className="pb-3">Entry</th><th className="pb-3">Description</th><th className="pb-3">Category</th><th className="pb-3">Amount</th><th className="pb-3">Status</th></tr></thead><tbody>{entries.map((entry) => <tr key={entry.id} className="border-t border-slate-100 dark:border-slate-800"><td className="py-3"><Link className="font-semibold text-primary" to={`/app/entries/${entry.id}`}>{entry.id}</Link></td><td className="max-w-[360px] py-3"><p className="line-clamp-2" title={entry.description}>{entry.description}</p></td><td className="py-3">{entry.category}</td><td className="py-3 font-semibold">{entry.amount}</td><td className="py-3"><Badge variant={entry.status.includes("failed") ? "danger" : entry.status.includes("Pending") ? "warning" : "success"}>{entry.status}</Badge></td></tr>)}</tbody></table></div></CardContent></Card>;
}

export function CategoryBreakdownChart({ data }: { data: RoleDashboardDefinition["categoryBreakdown"] }) {
  const fills = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b"];
  return <Card><CardHeader><CardTitle>Category breakdown</CardTitle><CardDescription>Current financial-entry classification mix.</CardDescription></CardHeader><CardContent>{data.length ? <><div className="h-64"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" nameKey="category" innerRadius={58} outerRadius={88} paddingAngle={4}>{data.map((item, index) => <Cell key={item.category} fill={fills[index % fills.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div><div className="grid grid-cols-2 gap-2">{data.map((item, index) => <div key={item.category} className="flex items-center justify-between text-sm"><span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: fills[index % fills.length] }} />{item.category}</span><span className="font-semibold">{item.value}%</span></div>)}</div></> : <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500 dark:border-slate-700">No classified entries are available yet.</div>}</CardContent></Card>;
}

export function AuditActivityCard({ events }: { events: RoleDashboardDefinition["auditActivity"] }) {
  return <Card><CardHeader><CardTitle>Audit activity</CardTitle><CardDescription>Recent immutable user and system actions.</CardDescription></CardHeader><CardContent className="space-y-4">{events.map((event) => <div key={event.id} className="flex gap-3"><div className="mt-1 h-2.5 w-2.5 rounded-full bg-indigo-500" /><div><p className="text-sm font-semibold">{event.action}</p><p className="text-xs text-slate-500">{event.actor} · {event.timestamp}</p></div></div>)}<Button asChild variant="outline" size="sm"><Link to="/app/audit">View audit log</Link></Button></CardContent></Card>;
}

export function QuickActionsPanel({ actions, readOnly }: { actions: RoleDashboardDefinition["quickActions"]; readOnly?: boolean }) {
  return <Card><CardHeader><CardTitle>Quick actions</CardTitle><CardDescription>{readOnly ? "Navigation only. Mutating actions are disabled for this role." : "Permission-aware shortcuts for your current role."}</CardDescription></CardHeader><CardContent className="grid gap-2">{actions.map((action) => <Button key={action.label} asChild variant="outline" className="justify-start"><Link to={action.href}>{action.label}</Link></Button>)}</CardContent></Card>;
}
