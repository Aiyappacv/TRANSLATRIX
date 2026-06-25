import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { Banknote, CircleDollarSign, Download, FileText, ReceiptText } from "lucide-react";
import type { PlatformInvoice } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { DataTable } from "@/components/common/DataTable";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PlatformStatusBadge } from "@/components/super-admin/PlatformStatusBadge";
import { downloadCsv, downloadJson } from "@/utils/downloads";
import { formatCurrency, formatDate } from "@/utils/formatters";

export function SuperAdminBillingPage() {
  const [selectedInvoice, setSelectedInvoice] = useState<PlatformInvoice | null>(null);
  const invoices = useQuery({ queryKey: ["super-admin", "billing"], queryFn: superAdminApi.getInvoices });
  const data = invoices.data ?? [];
  const columns = useMemo<ColumnDef<PlatformInvoice>[]>(() => [
    { accessorKey: "id", header: "Invoice" },
    { accessorKey: "companyName", header: "Company" },
    { accessorKey: "billingPeriod", header: "Billing period" },
    { accessorKey: "amount", header: "Amount", cell: ({ row }) => formatCurrency(row.original.amount, row.original.currency) },
    { accessorKey: "status", header: "Status", cell: ({ row }) => <PlatformStatusBadge status={row.original.status} /> },
    { accessorKey: "issuedAt", header: "Issued", cell: ({ row }) => formatDate(row.original.issuedAt) },
    { accessorKey: "dueAt", header: "Due", cell: ({ row }) => formatDate(row.original.dueAt) },
    { id: "actions", header: "Actions", cell: ({ row }) => <Button variant="outline" size="sm" onClick={() => setSelectedInvoice(row.original)}><FileText className="h-4 w-4" />View invoice</Button> },
  ], []);
  if (invoices.isLoading) return <LoadingState label="Loading billing records..." />;
  const total = data.reduce((sum, invoice) => sum + invoice.amount, 0);
  const exportReport = () => downloadCsv(
    `translatrix-billing-${new Date().toISOString().slice(0, 10)}.csv`,
    ["Invoice", "Company", "Period", "Amount", "Currency", "Status", "Issued", "Due"],
    data.map((invoice) => [invoice.id, invoice.companyName, invoice.billingPeriod, invoice.amount, invoice.currency, invoice.status, invoice.issuedAt, invoice.dueAt]),
  );
  return (
    <>
      <PageHeader eyebrow="Revenue operations" title="Billing" description="Review tenant invoices, payment status, billing periods, and revenue exceptions." actions={<Button onClick={exportReport} disabled={!data.length}><Download className="h-4 w-4" />Export billing report</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Invoiced this period" value={formatCurrency(total, "USD")} icon={CircleDollarSign} />
        <MetricCard label="Collected" value={formatCurrency(data.filter((invoice) => invoice.status === "paid").reduce((sum, invoice) => sum + invoice.amount, 0), "USD")} tone="success" icon={Banknote} />
        <MetricCard label="Past due" value={String(data.filter((invoice) => invoice.status === "past_due").length)} tone="danger" icon={ReceiptText} />
      </div>
      <Card><CardContent className="pt-6"><DataTable columns={columns} data={data} searchPlaceholder="Search invoices, companies, periods..." exportFileName="billing-invoices" /></CardContent></Card>

      <Dialog open={Boolean(selectedInvoice)} onOpenChange={(open) => !open && setSelectedInvoice(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Invoice {selectedInvoice?.id}</DialogTitle><DialogDescription>{selectedInvoice?.companyName} · {selectedInvoice?.billingPeriod}</DialogDescription></DialogHeader>
          {selectedInvoice ? <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">{[
              ["Company", selectedInvoice.companyName], ["Amount", formatCurrency(selectedInvoice.amount, selectedInvoice.currency)], ["Issued", formatDate(selectedInvoice.issuedAt)], ["Due", formatDate(selectedInvoice.dueAt)],
            ].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-semibold">{value}</p></div>)}</div>
            <div className="flex items-center justify-between rounded-xl border border-slate-200 p-3 dark:border-slate-800"><span className="text-sm font-semibold">Payment status</span><PlatformStatusBadge status={selectedInvoice.status} /></div>
            <div className="flex justify-end"><Button variant="outline" onClick={() => downloadJson(`${selectedInvoice.id}.json`, selectedInvoice)}><Download className="h-4 w-4" />Download invoice</Button></div>
          </div> : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
