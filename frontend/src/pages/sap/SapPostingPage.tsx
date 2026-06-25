import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Download,
  Eye,
  FileJson2,
  MoreHorizontal,
  RefreshCw,
  RotateCcw,
  Send,
  Settings2,
  TriangleAlert,
} from "lucide-react";
import type { SapPostingRecord, SapPostingStatus } from "@/types";
import { sapApi } from "@/services/sapApi";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { JsonPayloadEditor } from "@/components/common/JsonPayloadEditor";
import { MetricCard } from "@/components/common/MetricCard";
import { Can } from "@/components/common/Can";
import { SapPostingStatusBadge } from "@/components/sap/SapPostingStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/useToast";
import { formatCurrency } from "@/utils/formatters";
import { permissions } from "@/utils/permissions";

const approvalTone = {
  approved: "success",
  pending: "warning",
  rejected: "danger",
  second_approval_required: "info",
} as const;

function downloadJson(filename: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function SapPostingPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<"all" | SapPostingStatus>(
    "all",
  );
  const [preview, setPreview] = useState<SapPostingRecord | null>(null);
  const [errorRecord, setErrorRecord] = useState<SapPostingRecord | null>(null);

  const postings = useQuery({
    queryKey: ["sap-postings"],
    queryFn: sapApi.getPostingRecords,
  });
  const configuration = useQuery({
    queryKey: ["sap-posting-configuration"],
    queryFn: sapApi.getPostingConfigurationStatus,
  });
  const execute = useMutation({
    mutationFn: ({ id, retry }: { id: string; retry: boolean }) =>
      retry ? sapApi.retryPosting(id) : sapApi.executePosting(id),
    onSuccess: (record) => {
      queryClient.invalidateQueries({ queryKey: ["sap-postings"] });
      queryClient.setQueryData(["sap-posting", record.id], record);
      toast.success(
        "SAP posting completed",
        `Document ${record.sapDocumentNumber} was created successfully.`,
      );
    },
    onError: (error) =>
      toast.error(
        "SAP posting failed",
        error instanceof Error
          ? error.message
          : "The connector returned an unexpected error.",
      ),
  });

  const records = postings.data ?? [];
  const sapPostingEnabled = configuration.data?.canPost === true;
  const filtered =
    statusFilter === "all"
      ? records
      : records.filter((record) => record.sapStatus === statusFilter);
  const posted = records.filter(
    (record) => record.sapStatus === "posted",
  ).length;
  const failed = records.filter(
    (record) => record.sapStatus === "failed",
  ).length;
  const ready = records.filter((record) => record.sapStatus === "ready").length;
  const completed = posted + failed;
  const successRate = completed ? Math.round((posted / completed) * 100) : 0;

  const columns = useMemo<ColumnDef<SapPostingRecord>[]>(
    () => [
      {
        accessorKey: "entryId",
        header: "Entry ID",
        cell: ({ row }) => (
          <Link
            className="font-semibold text-primary hover:underline"
            to={`/app/posting/sap/${row.original.id}`}
          >
            {row.original.entryId}
          </Link>
        ),
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: ({ row }) => (
          <Badge variant="neutral">{row.original.category}</Badge>
        ),
      },
      {
        accessorKey: "sapTCode",
        header: "SAP T-Code",
        cell: ({ row }) => (
          <Badge variant="brand">{row.original.sapTCode}</Badge>
        ),
      },
      {
        accessorKey: "sapProcess",
        header: "SAP process",
        cell: ({ row }) => (
          <span
            className="block max-w-52 truncate"
            title={row.original.sapProcess}
          >
            {row.original.sapProcess}
          </span>
        ),
      },
      {
        accessorKey: "companyCode",
        header: "Company code",
        cell: ({ row }) => (
          <span className="font-mono text-xs font-semibold">
            {row.original.companyCode}
          </span>
        ),
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: ({ row }) => (
          <span className="font-semibold tabular-nums">
            {formatCurrency(row.original.amount, row.original.currency)}
          </span>
        ),
      },
      { accessorKey: "currency", header: "Currency" },
      {
        accessorKey: "approvalStatus",
        header: "Approval status",
        cell: ({ row }) => (
          <Badge variant={approvalTone[row.original.approvalStatus]}>
            {row.original.approvalStatus.replaceAll("_", " ")}
          </Badge>
        ),
      },
      {
        accessorKey: "sapStatus",
        header: "SAP status",
        cell: ({ row }) => (
          <SapPostingStatusBadge status={row.original.sapStatus} />
        ),
      },
      {
        accessorKey: "sapDocumentNumber",
        header: "SAP document number",
        cell: ({ row }) =>
          row.original.sapDocumentNumber ? (
            <span className="font-mono text-xs font-semibold">
              {row.original.sapDocumentNumber}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          ),
      },
      {
        id: "actions",
        header: "Actions",
        enableHiding: false,
        cell: ({ row }) => {
          const record = row.original;
          const pending =
            execute.isPending && execute.variables?.id === record.id;
          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Actions for ${record.entryId}`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onSelect={() => setPreview(record)}>
                  <FileJson2 className="mr-2 h-4 w-4" />
                  Preview SAP payload
                </DropdownMenuItem>
                <DropdownMenuItem
                  onSelect={() => navigate(`/app/posting/sap/${record.id}`)}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  Open posting detail
                </DropdownMenuItem>
                {record.sapStatus === "ready" ? (
                  <Can permissions={[permissions.postingExecute]}>
                    <DropdownMenuItem
                      disabled={pending || !sapPostingEnabled}
                      onSelect={() =>
                        execute.mutate({ id: record.id, retry: false })
                      }
                    >
                      <Send className="mr-2 h-4 w-4" />
                      Post to SAP
                    </DropdownMenuItem>
                  </Can>
                ) : null}
                {record.sapStatus === "failed" ? (
                  <Can permissions={[permissions.postingRetry]}>
                    <DropdownMenuItem
                      disabled={pending || !sapPostingEnabled}
                      onSelect={() =>
                        execute.mutate({ id: record.id, retry: true })
                      }
                    >
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Retry failed posting
                    </DropdownMenuItem>
                  </Can>
                ) : null}
                {record.response ? (
                  <Can permissions={[permissions.postingDownload]}>
                    <DropdownMenuItem
                      onSelect={() =>
                        downloadJson(
                          `${record.entryId}-sap-response.json`,
                          record.response,
                        )
                      }
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download response
                    </DropdownMenuItem>
                  </Can>
                ) : null}
                {record.errorMessage ? (
                  <DropdownMenuItem
                    className="text-red-600"
                    onSelect={() => setErrorRecord(record)}
                  >
                    <TriangleAlert className="mr-2 h-4 w-4" />
                    View error
                  </DropdownMenuItem>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          );
        },
      },
    ],
    [execute, navigate, sapPostingEnabled],
  );

  return (
    <>
      <PageHeader
        eyebrow="Phase 9 · Posting"
        title="SAP S/4HANA posting"
        description="Submit only approved and immutable accounting entries, inspect canonical payloads, and trace every SAP response."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => postings.refetch()}
              disabled={postings.isFetching}
            >
              <RefreshCw
                className={`h-4 w-4 ${postings.isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            <Can permissions={[permissions.integrationsManage]}>
              <Button asChild variant="outline">
                <Link to="/app/integrations/sap/settings">
                  <Settings2 className="h-4 w-4" />
                  SAP settings
                </Link>
              </Button>
            </Can>
          </div>
        }
      />

      {!sapPostingEnabled ? (
        <div className="mb-6 flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-100">
          <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Posting actions are disabled</p>
            <p className="mt-1">
              {configuration.isError
                ? "SAP configuration status could not be verified. Refresh the page before attempting a posting."
                : (configuration.data?.message ??
                  "Checking SAP configuration status...")}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Ready to post"
          value={String(ready)}
          delta="Approved and payload locked"
          tone="info"
        />
        <MetricCard
          label="Posted"
          value={String(posted)}
          delta="Documents created in SAP"
          tone="success"
        />
        <MetricCard
          label="Failed"
          value={String(failed)}
          delta="Require correction or retry"
          tone={failed ? "danger" : "neutral"}
        />
        <MetricCard
          label="Posting success"
          value={`${successRate}%`}
          delta="Completed posting attempts"
          tone="success"
        />
      </div>

      <Card className="mt-6">
        <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Posting worklist</CardTitle>
            <CardDescription>
              Every action is permission-aware and uses an idempotent posting
              record.
            </CardDescription>
          </div>
          <div className="w-full md:w-56">
            <Select
              value={statusFilter}
              onValueChange={(value) =>
                setStatusFilter(value as "all" | SapPostingStatus)
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Filter SAP status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All SAP statuses</SelectItem>
                <SelectItem value="ready">Ready</SelectItem>
                <SelectItem value="queued">Queued</SelectItem>
                <SelectItem value="posting">Posting</SelectItem>
                <SelectItem value="posted">Posted</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="reversed">Reversed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={filtered}
            searchPlaceholder="Search entry, T-Code, process, company code, or document..."
            exportFileName="sap-postings"
            dense
          />
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(preview)}
        onOpenChange={(open) => !open && setPreview(null)}
      >
        <DialogContent className="max-w-4xl p-0">
          <DialogHeader className="px-6 pt-6">
            <DialogTitle>SAP payload · {preview?.entryId}</DialogTitle>
            <DialogDescription>
              Read-only payload generated from the approved accounting entry.
            </DialogDescription>
          </DialogHeader>
          {preview ? (
            <div className="p-6 pt-2">
              <JsonPayloadEditor
                title="Canonical SAP payload"
                value={preview.payload}
                height={520}
              />
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(errorRecord)}
        onOpenChange={(open) => !open && setErrorRecord(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Posting error · {errorRecord?.entryId}</DialogTitle>
            <DialogDescription>
              The SAP response is preserved for audit and troubleshooting.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
            <p className="font-semibold">{errorRecord?.errorCode}</p>
            <p className="mt-1">{errorRecord?.errorMessage}</p>
          </div>
          {errorRecord?.response ? (
            <JsonPayloadEditor
              title="SAP error response"
              value={errorRecord.response}
              height={300}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
