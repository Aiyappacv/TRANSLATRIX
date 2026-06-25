import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, FileDown, RefreshCw, RotateCcw } from "lucide-react";
import type { TallyExportJob, TallyVoucherType } from "@/types";
import { tallyExportSchema, tallyVoucherTypes, type TallyExportForm } from "@/schemas/tallyExport.schema";
import { tallyExportApi } from "@/services/tallyExportApi";
import { companyApi } from "@/services/companyApi";
import { permissions } from "@/utils/permissions";
import { formatDateTime } from "@/utils/formatters";
import { useToast } from "@/hooks/useToast";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";
import { Can } from "@/components/common/Can";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const voucherLabels: Record<TallyVoucherType, string> = {
  purchase: "Purchase",
  sales: "Sales",
  journal: "Journal",
  payment: "Payment",
  receipt: "Receipt",
  contra: "Contra",
};

function monthStart() {
  const date = new Date();
  date.setDate(1);
  return date.toISOString().slice(0, 10);
}

const defaults: TallyExportForm = {
  companyId: "",
  companyCode: "",
  dateFrom: monthStart(),
  dateTo: new Date().toISOString().slice(0, 10),
  format: "xml",
  voucherTypes: ["purchase", "sales", "journal"],
  includeLedgers: true,
  includeCostCenters: true,
  includeTaxDetails: true,
};

function statusBadge(status: TallyExportJob["status"]) {
  const variant = status === "completed" ? "success" : status === "failed" ? "danger" : status === "processing" ? "info" : "warning";
  return <Badge variant={variant}>{status}</Badge>;
}

export function TallyExportPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const exportsQuery = useQuery({ queryKey: ["tally-exports"], queryFn: tallyExportApi.listExports });
  const companiesQuery = useQuery({ queryKey: ["companies", "tally-export"], queryFn: companyApi.getCompanies });
  const form = useForm<TallyExportForm>({ resolver: zodResolver(tallyExportSchema), defaultValues: defaults });
  useUnsavedChanges(form.formState.isDirty);

  const createExport = useMutation({
    mutationFn: tallyExportApi.createExport,
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["tally-exports"] });
      form.reset(defaults);
      toast.success("Tally export generated", `${job.recordsExported} records are ready for download.`);
    },
    onError: (error) => toast.error("Unable to generate Tally export", error instanceof Error ? error.message : "Unexpected export error."),
  });

  const retryExport = useMutation({
    mutationFn: tallyExportApi.retryExport,
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["tally-exports"] });
      toast.success("Tally export retried", `${job.recordsExported} records were generated.`);
    },
    onError: (error) => toast.error("Retry failed", error instanceof Error ? error.message : "Unexpected export error."),
  });

  const downloadExport = useMutation({
    mutationFn: tallyExportApi.downloadExport,
    onSuccess: (download) => toast.success("Download started", download.fileName),
    onError: (error) => toast.error("Download unavailable", error instanceof Error ? error.message : "Unable to get the export file."),
  });

  const columns: ColumnDef<TallyExportJob>[] = [
    { accessorKey: "id", header: "Export ID", cell: ({ row }) => <span className="font-mono text-xs">{row.original.id}</span> },
    { accessorKey: "companyCode", header: "Company", cell: ({ row }) => <div><p className="font-semibold">{row.original.companyCode}</p><p className="text-xs text-slate-500">{row.original.companyName}</p></div> },
    { accessorKey: "dateFrom", header: "Period", cell: ({ row }) => <span className="text-xs">{row.original.dateFrom} → {row.original.dateTo}</span> },
    { accessorKey: "format", header: "Format", cell: ({ row }) => <Badge variant="neutral">{row.original.format.toUpperCase()}</Badge> },
    { accessorKey: "recordsExported", header: "Records" },
    { accessorKey: "status", header: "Status", cell: ({ row }) => statusBadge(row.original.status) },
    { accessorKey: "createdAt", header: "Created", cell: ({ row }) => formatDateTime(row.original.createdAt) },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex gap-2">
          {row.original.status === "completed" ? <Button size="sm" variant="outline" disabled={downloadExport.isPending} onClick={() => downloadExport.mutate(row.original.id)}><Download className="h-4 w-4" />Download</Button> : null}
          {row.original.status === "failed" && row.original.retryable ? <Can permissions={[permissions.integrationsManage]}><ConfirmDialog destructive={false} title="Retry Tally export?" description="The backend will regenerate this export using the original date range, company, and voucher selections." confirmLabel="Retry export" onConfirm={async () => { await retryExport.mutateAsync(row.original.id); }} trigger={<Button size="sm" variant="outline"><RotateCcw className="h-4 w-4" />Retry</Button>} /></Can> : null}
        </div>
      ),
    },
  ];

  if (exportsQuery.isLoading) return <LoadingState label="Loading Tally exports..." />;
  if (exportsQuery.isError) return <ErrorState title="Tally exports unavailable" description={exportsQuery.error instanceof Error ? exportsQuery.error.message : "Unable to load export jobs."} onRetry={() => exportsQuery.refetch()} />;

  const selectedVouchers = form.watch("voucherTypes");
  const toggleVoucher = (voucher: TallyVoucherType, checked: boolean) => {
    const next = checked ? [...selectedVouchers, voucher] : selectedVouchers.filter((item) => item !== voucher);
    form.setValue("voucherTypes", [...new Set(next)], { shouldDirty: true, shouldValidate: true });
  };

  return (
    <>
      <PageHeader
        eyebrow="Enterprise integrations · TallyPrime"
        title="Tally export"
        description="Generate controlled Tally-compatible XML, JSON, or CSV packages through backend-managed export jobs."
        actions={<Button variant="outline" onClick={() => exportsQuery.refetch()}><RefreshCw className={`h-4 w-4 ${exportsQuery.isFetching ? "animate-spin" : ""}`} />Refresh</Button>}
      />

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader><CardTitle>Generate export</CardTitle><CardDescription>The backend validates company access, voucher eligibility, and export readiness before creating the file.</CardDescription></CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={form.handleSubmit((value) => createExport.mutate(value))}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="companyId">Company</Label>
                  <select id="companyId" className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" {...form.register("companyId")} onChange={(event) => {
                    form.register("companyId").onChange(event);
                    const company = companiesQuery.data?.find((item) => item.id === event.target.value);
                    form.setValue("companyCode", company?.defaultCompanyCode ?? "", { shouldDirty: true, shouldValidate: true });
                  }}>
                    <option value="">Select company</option>
                    {(companiesQuery.data ?? []).map((company) => <option key={company.id} value={company.id}>{company.tradingName || company.legalName}</option>)}
                  </select>
                  {form.formState.errors.companyId ? <p className="text-xs text-red-600">{form.formState.errors.companyId.message}</p> : null}
                </div>
                <div className="space-y-2"><Label htmlFor="companyCode">Company code</Label><Input id="companyCode" {...form.register("companyCode")} />{form.formState.errors.companyCode ? <p className="text-xs text-red-600">{form.formState.errors.companyCode.message}</p> : null}</div>
                <div className="space-y-2"><Label htmlFor="dateFrom">From date</Label><Input id="dateFrom" type="date" {...form.register("dateFrom")} /></div>
                <div className="space-y-2"><Label htmlFor="dateTo">To date</Label><Input id="dateTo" type="date" {...form.register("dateTo")} />{form.formState.errors.dateTo ? <p className="text-xs text-red-600">{form.formState.errors.dateTo.message}</p> : null}</div>
                <div className="space-y-2 md:col-span-2"><Label htmlFor="format">Export format</Label><select id="format" className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" {...form.register("format")}><option value="xml">Tally XML</option><option value="json">JSON</option><option value="csv">CSV</option></select></div>
              </div>

              <div>
                <Label>Voucher types</Label>
                <div className="mt-3 grid gap-3 rounded-2xl border border-slate-200 p-4 sm:grid-cols-2 dark:border-slate-800">
                  {tallyVoucherTypes.map((voucher) => <Checkbox key={voucher} label={voucherLabels[voucher]} checked={selectedVouchers.includes(voucher)} onChange={(event) => toggleVoucher(voucher, event.target.checked)} />)}
                </div>
                {form.formState.errors.voucherTypes ? <p className="mt-2 text-xs text-red-600">{form.formState.errors.voucherTypes.message}</p> : null}
              </div>

              <div className="grid gap-3 rounded-2xl bg-slate-50 p-4 dark:bg-slate-900 md:grid-cols-3">
                <Controller control={form.control} name="includeLedgers" render={({ field }) => <Checkbox label="Include ledger masters" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
                <Controller control={form.control} name="includeCostCenters" render={({ field }) => <Checkbox label="Include cost centres" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
                <Controller control={form.control} name="includeTaxDetails" render={({ field }) => <Checkbox label="Include GST/tax details" checked={field.value} onChange={(event) => field.onChange(event.target.checked)} />} />
              </div>

              <Can permissions={[permissions.integrationsManage]} fallback={<p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">You have read-only access. An Integration Manager or Company Admin must generate exports.</p>}>
                <ConfirmDialog
                  destructive={false}
                  title="Generate Tally export?"
                  description="This creates a backend export job using the selected company, accounting period, and voucher types."
                  confirmLabel="Generate export"
                  onConfirm={form.handleSubmit((value) => createExport.mutateAsync(value))}
                  trigger={<Button type="button" className="w-full" disabled={createExport.isPending}><FileDown className="h-4 w-4" />{createExport.isPending ? "Generating..." : "Generate Tally export"}</Button>}
                />
              </Can>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Backend contract</CardTitle><CardDescription>Endpoints expected by this frontend patch.</CardDescription></CardHeader>
          <CardContent className="space-y-4 text-sm">
            {["POST /integrations/tallyprime/exports", "GET /integrations/tallyprime/exports", "POST /integrations/tallyprime/exports/:exportId/retry", "GET /integrations/tallyprime/exports/:exportId/download"].map((endpoint) => <div key={endpoint} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-xs dark:border-slate-800 dark:bg-slate-900">{endpoint}</div>)}
            <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-indigo-900 dark:border-indigo-900/60 dark:bg-indigo-950/30 dark:text-indigo-200"><p className="font-semibold">Production behavior</p><p className="mt-1 text-xs leading-5">Every action uses the authenticated tenant-aware backend API and includes the active Authorization, tenant, and company context.</p></div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Export history</CardTitle><CardDescription>Completed, processing, and failed Tally export jobs with retry and download actions.</CardDescription></CardHeader>
        <CardContent><DataTable columns={columns} data={exportsQuery.data ?? []} searchPlaceholder="Search export ID, company, format, or status..." exportFileName="tally-export-history" dense /></CardContent>
      </Card>
    </>
  );
}
