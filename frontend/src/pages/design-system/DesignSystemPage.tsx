import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CheckCircle2, CircleAlert, Palette, PanelRightOpen, Table2 } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CategoryBadge } from "@/components/common/CategoryBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { AlertCard } from "@/components/common/AlertCard";
import { TaskCard } from "@/components/common/TaskCard";
import { Timeline } from "@/components/common/Timeline";
import { FileDropzone } from "@/components/common/FileDropzone";
import { DataTable } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Alert } from "@/components/ui/alert";
import { Modal, ModalContent, ModalDescription, ModalHeader, ModalTitle } from "@/components/ui/modal";
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { useToast } from "@/hooks/useToast";

const colors = [
  ["Primary", "#4F46E5"], ["Violet", "#7C3AED"], ["Deep navy", "#0F172A"],
  ["Success", "#059669"], ["Warning", "#D97706"], ["Error", "#DC2626"], ["Processing", "#2563EB"],
  ["Page", "#F8FAFC"], ["Card", "#FFFFFF"], ["Border", "#E2E8F0"], ["Primary text", "#0F172A"], ["Muted text", "#64748B"],
];

const chartData: Array<{ label: string; files: number }> = [];

interface TableRow { entry: string; vendor: string; amount: string; status: string }
const rows: TableRow[] = [];
const columns: ColumnDef<TableRow>[] = [
  { accessorKey: "entry", header: "Entry" }, { accessorKey: "vendor", header: "Vendor" },
  { accessorKey: "amount", header: "Amount" }, { accessorKey: "status", header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
];

export function DesignSystemPage() {
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <PageHeader eyebrow="Phase 1" title="Design System" description="Enterprise AI-finance SaaS tokens, typography, spacing, components, dashboard patterns, states, and accessibility examples." />
      <div className="grid gap-6">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Palette className="h-5 w-5 text-primary" />Brand and semantic colors</CardTitle><CardDescription>Light and dark-mode-ready variables used consistently across finance, review, posting, and audit workflows.</CardDescription></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-6">{colors.map(([name, hex]) => <div key={name} className="rounded-2xl border border-slate-200 p-3 dark:border-slate-800"><div className="h-14 rounded-xl border border-black/5" style={{ background: hex }} /><p className="mt-3 font-semibold">{name}</p><p className="font-mono text-xs text-slate-500">{hex}</p></div>)}</CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Typography and spacing scale</CardTitle><CardDescription>Inter/Aptos-style hierarchy with compact, readable finance tables and 20–24px card padding.</CardDescription></CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="space-y-4">
              <div><p className="text-xs uppercase tracking-widest text-slate-500">H1 · 28–32 / 700</p><p className="text-3xl font-bold tracking-tight">Financial operations overview</p></div>
              <div><p className="text-xs uppercase tracking-widest text-slate-500">H2 · 22–24 / 700</p><p className="text-2xl font-bold">Review queue and exceptions</p></div>
              <div><p className="text-xs uppercase tracking-widest text-slate-500">H3 · 18 / 600</p><p className="text-lg font-semibold">Accounting entry validation</p></div>
              <div><p className="text-xs uppercase tracking-widest text-slate-500">Body · 14–15</p><p className="text-sm text-slate-600 dark:text-slate-300">Use clear labels, explicit status communication, tabular numerals, and concise helper text.</p></div>
            </div>
            <div className="grid grid-cols-4 gap-2 self-start">
              {[4, 8, 12, 16, 20, 24, 32, 40].map((space) => <div key={space} className="rounded-xl border border-slate-200 p-2 text-center text-xs dark:border-slate-800"><div className="mx-auto rounded bg-primary/20" style={{ width: Math.min(space, 40), height: Math.min(space, 40) }} /><p className="mt-2">{space}px</p></div>)}
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-4">
          <MetricCard label="KPI number" value="0" tone="success" icon={CheckCircle2} />
          <MetricCard label="Review queue" value="0" tone="warning" icon={CircleAlert} />
          <MetricCard label="Tables" value="0" tone="info" icon={Table2} />
          <MetricCard label="Failures" value="0" tone="danger" icon={CircleAlert} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Card>
            <CardHeader><CardTitle>Data table pattern</CardTitle><CardDescription>Searchable, paginated, dense, responsive, and status-aware.</CardDescription></CardHeader>
            <CardContent><DataTable columns={columns} data={rows} dense searchPlaceholder="Search entries..." /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Dashboard chart pattern</CardTitle><CardDescription>Readable labels and tooltip treatment for processing volume.</CardDescription></CardHeader>
            <CardContent className="h-[310px]">
              <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ left: -16, right: 8, top: 8 }}><defs><linearGradient id="filesGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="currentColor" stopOpacity={0.28} /><stop offset="95%" stopColor="currentColor" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" tickLine={false} axisLine={false} /><YAxis tickLine={false} axisLine={false} /><Tooltip /><Area type="monotone" dataKey="files" stroke="currentColor" fill="url(#filesGradient)" className="text-primary" /></AreaChart></ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Buttons, badges, confidence, modal, and drawer</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button onClick={() => toast.success("Primary action", "Interactive design-system control executed.")}>Primary action</Button><Button variant="outline" onClick={() => toast.info("Secondary action", "Interactive design-system control executed.")}>Secondary</Button><Button variant="success" onClick={() => toast.success("Approved", "Approval interaction example completed.")}>Approve</Button><Button variant="destructive" onClick={() => toast.error("Rejected", "Destructive interaction example completed.")}>Reject</Button>
            <Badge variant="brand">Brand</Badge><Badge variant="success">Success</Badge><Badge variant="warning">Warning</Badge><Badge variant="danger">Danger</Badge>
            <StatusBadge status="needs_review" /><CategoryBadge category="Expenses" /><ConfidenceBadge value={0.92} /><ConfidenceBadge value={0.76} />
            <Button variant="outline" onClick={() => setModalOpen(true)}>Open modal</Button><Button variant="outline" onClick={() => setDrawerOpen(true)}><PanelRightOpen className="h-4 w-4" />Open drawer</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Forms and accessibility examples</CardTitle><CardDescription>Visible labels, keyboard focus, input hierarchy, confirmations, and semantic feedback.</CardDescription></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input aria-label="Global search example" placeholder="Search vendors, entries, SAP documents" />
            <Input aria-label="Document date example" type="date" />
            <Textarea aria-label="Reviewer comments example" placeholder="Reviewer comments" />
            <div className="space-y-3"><Checkbox label="Original document reviewed" /><Switch label="MFA required" /><Alert tone="info">Keyboard focus, ARIA labels, and confirmation dialogs are required for financial actions.</Alert></div>
          </CardContent>
        </Card>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card><CardHeader><CardTitle>File dropzone</CardTitle></CardHeader><CardContent><FileDropzone /></CardContent></Card>
          <Card><CardHeader><CardTitle>Timeline</CardTitle></CardHeader><CardContent><Timeline items={[]} /></CardContent></Card>
        </div>
        <div className="grid gap-4 md:grid-cols-2"><AlertCard title="Validation warning" description="Low mapping confidence requires reviewer confirmation." /><TaskCard title="Review supplier invoice" description="Confirm category, SAP T-Code, and debit-credit balance." onAction={() => toast.info("Review task opened", "Task-card interaction example completed.")} /></div>
      </div>

      <Modal open={modalOpen} onOpenChange={setModalOpen}><ModalContent><ModalHeader><ModalTitle>Confirm financial action</ModalTitle><ModalDescription>Modal pattern for decisions that change approval or posting state.</ModalDescription></ModalHeader><div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setModalOpen(false)}>Cancel</Button><Button variant="success" onClick={() => setModalOpen(false)}>Confirm</Button></div></ModalContent></Modal>
      <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}><DrawerContent><DrawerHeader><DrawerTitle>Audit detail drawer</DrawerTitle><DrawerDescription>Side panel pattern for metadata, old/new values, and request context without leaving the current page.</DrawerDescription></DrawerHeader><div className="space-y-3 text-sm"><div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">Entity</p><p className="font-semibold">Financial entry</p></div><div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">Change</p><p className="font-semibold">SAP T-Code change</p></div></div><DrawerFooter><Button variant="outline" onClick={() => setDrawerOpen(false)}>Close</Button></DrawerFooter></DrawerContent></Drawer>
    </>
  );
}
