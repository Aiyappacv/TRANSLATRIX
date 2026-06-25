import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Download,
  Eye,
  FileCode,
  FileText,
  ListChecks,
  Loader2,
  MoreHorizontal,
  RefreshCcw,
  Search,
  Sparkles,
  Trash2,
  Workflow,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { documentRegistryApi } from "@/services/documentRegistryApi";
import { ingestionApi } from "@/services/ingestionApi";
import { fileApi } from "@/services/fileApi";
import type { DocumentRegistryEntry } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

const STATUS_COLORS: Record<string, string> = {
  uploaded: "bg-amber-100 text-amber-800 border-amber-300 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300",
  processing: "bg-blue-100 text-blue-800 border-blue-300 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300",
  extracting: "bg-blue-100 text-blue-800 border-blue-300 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300",
  ready_for_extraction: "bg-indigo-100 text-indigo-800 border-indigo-300 dark:border-indigo-900/60 dark:bg-indigo-950/40 dark:text-indigo-300",
  needs_review: "bg-amber-100 text-amber-800 border-amber-300 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300",
  completed: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300",
  validation_failed: "bg-red-100 text-red-800 border-red-300 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300",
  failed: "bg-red-100 text-red-800 border-red-300 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300",
  queued: "bg-slate-100 text-slate-700 border-slate-300 dark:border-slate-800/60 dark:bg-slate-950/40 dark:text-slate-300",
};

const STATUS_LABELS: Record<string, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  extracting: "Extracting",
  ready_for_extraction: "Ready for extraction",
  needs_review: "Pending review",
  completed: "Completed",
  validation_failed: "Validation failed",
  failed: "Failed",
  queued: "Queued",
};

const IN_PROGRESS_STATUSES = new Set(["uploaded", "processing", "extracting", "ready_for_extraction"]);

function formatStatus(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

function statusClasses(status: string | null | undefined): string {
  if (!status) return "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200";
  return STATUS_COLORS[status] || "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200";
}

function StatusBadgeCell({ status }: { status: string | null | undefined }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusClasses(status)}`}>
      {formatStatus(status)}
    </span>
  );
}

function confidenceTone(value: number | null): string {
  if (value == null) return "text-slate-400 dark:text-slate-600";
  if (value >= 0.95) return "text-emerald-600 dark:text-emerald-400";
  if (value >= 0.8) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** The Document Registry table: search, status filter, sort/paginate, CSV/Excel
 * export, and a full actions menu per row. Embedded directly inside the Document
 * Extraction page rather than living behind its own nav entry. */
export function DocumentRegistryTable() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [deleteEntry, setDeleteEntry] = useState<DocumentRegistryEntry | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const registryQuery = useQuery({
    queryKey: ["document-registry", page, search, statusFilter],
    queryFn: () =>
      documentRegistryApi.list({
        page,
        page_size: 50,
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
    refetchInterval: (query) => {
      const entries = query.state.data?.entries;
      if (!entries || entries.length === 0) return 10000;
      return entries.some((e) => IN_PROGRESS_STATUSES.has(e.status)) ? 3000 : false;
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => documentRegistryApi.reprocess(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-registry"] });
      toast.success("Document reprocessed");
    },
    onError: (err: Error) => toast.error(`Reprocess failed: ${err.message}`),
  });

  const extractMutation = useMutation({
    mutationFn: (entryId: string) => ingestionApi.prepareExtraction(entryId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["document-registry"] });
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
      toast.success("Extraction pipeline opening");
      navigate(result.redirect_url);
    },
    onError: (err: Error) => toast.error(`Extraction failed: ${err.message}`),
  });

  const handleDeleteConfirm = async () => {
    if (!deleteEntry) return;
    setIsDeleting(true);
    try {
      await documentRegistryApi.delete(deleteEntry.id);
      queryClient.invalidateQueries({ queryKey: ["document-registry"] });
      toast.success("Registry entry deleted");
      setIsDeleteOpen(false);
      setDeleteEntry(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setIsDeleting(false);
    }
  };

  const columns = useMemo<ColumnDef<DocumentRegistryEntry>[]>(
    () => [
      {
        accessorKey: "id",
        header: "Document ID",
        cell: ({ row }) => (
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono font-semibold text-slate-800 dark:bg-slate-900 dark:text-slate-200" title={row.original.id}>
            {row.original.id}
          </code>
        ),
      },
      {
        accessorKey: "originalFileName",
        header: "File Name",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="max-w-[220px] truncate font-medium" title={row.original.originalFileName}>
              {row.original.originalFileName}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "documentType",
        header: "Document Type",
        cell: ({ row }) => {
          const dt = row.original.documentType;
          if (dt === "invoice") {
            return (
              <span className="inline-flex items-center rounded-full border border-blue-300 bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                Commercial Invoice
              </span>
            );
          }
          if (dt === "banking_document") {
            return (
              <span className="inline-flex items-center rounded-full border border-violet-300 bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-300">
                Banking Document
              </span>
            );
          }
          return <span className="text-sm text-slate-400 dark:text-slate-600">—</span>;
        },
      },
      {
        accessorKey: "uploadedAt",
        header: "Upload Date",
        cell: ({ row }) => <span className="text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">{row.original.uploadedAt ? formatDateTime(row.original.uploadedAt) : "—"}</span>,
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadgeCell status={row.original.status} />,
      },
      {
        accessorKey: "overallConfidence",
        header: "Confidence Score",
        cell: ({ row }) => {
          const value = row.original.overallConfidence;
          return <span className={`font-semibold tabular-nums text-sm ${confidenceTone(value)}`}>{value != null ? `${Math.round(value * 100)}%` : "—"}</span>;
        },
      },
      {
        accessorKey: "ocrEngine",
        header: "OCR Model Used",
        cell: ({ row }) => <Badge variant="neutral" className="text-xs">{row.original.ocrEngine || "—"}</Badge>,
      },
      {
        accessorKey: "processingTimeSeconds",
        header: "Processing Time",
        cell: ({ row }) => <span className="text-sm text-slate-500 dark:text-slate-400">{row.original.processingTimeSeconds != null ? `${row.original.processingTimeSeconds.toFixed(1)}s` : "—"}</span>,
      },
      {
        accessorKey: "languageDetected",
        header: "Language",
        cell: ({ row }) => <span className="uppercase text-xs text-slate-500 dark:text-slate-400">{row.original.languageDetected || "—"}</span>,
      },
      {
        accessorKey: "uploadedBy",
        header: "Uploaded By",
        cell: ({ row }) => <span className="text-sm text-slate-600 dark:text-slate-400">{row.original.uploadedBy || "—"}</span>,
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => {
          const entry = row.original;
          const activeExtractionEntryId = extractMutation.variables as string | undefined;
          const isPipelineActive = ["processing", "extracting"].includes(entry.status ?? "");
          const isMutatingThisRow = Boolean(
            entry.intakeRegistryId &&
            extractMutation.isPending &&
            activeExtractionEntryId === entry.intakeRegistryId
          );
          const handleExtract = () => {
            if (entry.intakeRegistryId) {
              extractMutation.mutate(entry.intakeRegistryId);
            } else {
              navigate(`/app/ingestion/data-ingestion/document-extraction?fileId=${entry.id}`);
            }
          };
          return (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 border-emerald-200 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-900 dark:text-emerald-400 dark:hover:bg-emerald-950/40"
                onClick={handleExtract}
                disabled={isMutatingThisRow || isPipelineActive}
                title={entry.intakeRegistryId ? "Open extraction pipeline" : "View extraction workspace"}
              >
                {isMutatingThisRow || isPipelineActive ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    {isMutatingThisRow ? "Opening..." : "Processing..."}
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                    Extract Document
                  </>
                )}
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8" aria-label={`Actions for ${entry.originalFileName}`}>
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onSelect={() => navigate(`/app/files/registry/${entry.id}`)}>
                    <Eye className="mr-2 h-4 w-4" />
                    View Document
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => navigate(`/app/files/registry/${entry.id}?tab=fields`)}>
                    <ListChecks className="mr-2 h-4 w-4" />
                    View Extracted Fields
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => navigate(`/app/files/registry/${entry.id}?tab=ocr`)}>
                    <FileCode className="mr-2 h-4 w-4" />
                    View Extraction Report
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => navigate(`/app/files/registry/${entry.id}?tab=logs`)}>
                    <Workflow className="mr-2 h-4 w-4" />
                    View Processing Logs
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => reprocessMutation.mutate(entry.id)} disabled={reprocessMutation.isPending}>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Reprocess Document
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => fileApi.downloadFile(entry.id, entry.originalFileName)}>
                    <Download className="mr-2 h-4 w-4" />
                    Download Original File
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => {
                    fileApi.downloadExtractionJson(entry.id, `${entry.originalFileName}.json`)
                      .catch((err) => toast.error(err instanceof Error ? err.message : "JSON download failed"));
                  }}>
                    <FileCode className="mr-2 h-4 w-4" />
                    Download Extracted JSON
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
                aria-label={`Delete ${entry.originalFileName}`}
                title="Delete Registry Entry"
                onClick={() => {
                  setDeleteEntry(entry);
                  setIsDeleteOpen(true);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          );
        },
      },
    ],
    [
      navigate,
      reprocessMutation.isPending,
      reprocessMutation.mutate,
      extractMutation.isPending,
      extractMutation.mutate,
      extractMutation.variables,
    ],
  );

  const data = registryQuery.data?.entries ?? [];
  const total = registryQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 50));

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: totalPages,
  });

  return (
    <>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3 flex-wrap gap-2">
          <CardTitle>Document Registry</CardTitle>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative w-56">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search file, invoice, vendor..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-8 h-9 text-sm"
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={(value) => {
                setStatusFilter(value);
                setPage(1);
              }}
            >
             <SelectTrigger className="h-9 w-44 text-sm">
               <SelectValue placeholder="Review status" />
             </SelectTrigger>
             <SelectContent>
                <SelectItem value="all">All review states</SelectItem>
                <SelectItem value="uploaded">Uploaded</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="needs_review">Pending review</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="validation_failed">Failed</SelectItem>
             </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={() => registryQuery.refetch()}>
              <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={() => documentRegistryApi.exportCsv({ search: search || undefined, status: statusFilter !== "all" ? statusFilter : undefined })}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => documentRegistryApi.exportXlsx({ search: search || undefined, status: statusFilter !== "all" ? statusFilter : undefined })}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Excel
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {registryQuery.isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : registryQuery.isError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">Failed to load document registry</p>
              <Button variant="outline" size="sm" onClick={() => registryQuery.refetch()}>
                Retry
              </Button>
            </div>
          ) : data.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="mb-3 h-10 w-10 text-slate-300 dark:text-slate-700" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">No documents in the registry yet</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Documents appear here automatically once they're processed through OCR/extraction.
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border dark:border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b dark:bg-slate-900 dark:border-slate-800">
                    {table.getHeaderGroups().map((hg) => (
                      <tr key={hg.id}>
                        {hg.headers.map((header) => (
                          <th key={header.id} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">
                            {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {table.getRowModel().rows.map((row) => (
                      <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/60 transition-colors">
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="px-4 py-3">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between mt-4 text-sm text-slate-500 dark:text-slate-400">
                <span>
                  Page {page} of {totalPages} ({total} total)
                </span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                    Previous
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Registry Entry?
            </DialogTitle>
            <DialogDescription>
              {deleteEntry
                ? `This permanently removes "${deleteEntry.originalFileName}" and all associated extraction results, entries, and review tasks. This cannot be undone.`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Delete Permanently"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
