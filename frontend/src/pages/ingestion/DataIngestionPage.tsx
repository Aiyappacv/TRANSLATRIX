import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  Database,
  FileText,
  AlertTriangle,
  Eye,
  Trash2,
  Sparkles,
  Search,
  X,
  Loader2,
  FileUp,
  FileWarning,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Check,
  Clock,
  MoreHorizontal,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ingestionApi } from "@/services/ingestionApi";
import type {
  IntakeRegistryEntry,
  IntakePreviewResponse,
  BatchUploadResponse,
  BulkDeleteResponse,
} from "@/types";
import { PageHeader } from "@/components/common/PageHeader";
import { MetricCard } from "@/components/common/MetricCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/useToast";
import { formatDateTime } from "@/utils/formatters";

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

const ACCEPTED_EXTENSIONS = ".pdf,.jpg,.jpeg,.png,.tiff,.tif,.xml,.json";
const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;

// "ready_for_extraction" is intentionally excluded: it's a stable state a
// document now rests in indefinitely until the user clicks "Extract
// Document" (upload and extraction are decoupled), not a transient one
// worth polling for.
const IN_PROGRESS_STATUSES = new Set([
  "uploading",
  "uploaded",
  "metadata_processing",
  "metadata_ready",
  "extracting",
]);

const STATUS_COLORS: Record<string, string> = {
  uploading: "bg-amber-100 text-amber-800 border-amber-300",
  uploaded: "bg-blue-100 text-blue-800 border-blue-300",
  metadata_processing: "bg-indigo-100 text-indigo-800 border-indigo-300",
  metadata_ready: "bg-teal-100 text-teal-800 border-teal-300",
  ready_for_extraction: "bg-emerald-100 text-emerald-800 border-emerald-300",
  extracting: "bg-blue-100 text-blue-800 border-blue-300",
  extracted: "bg-green-100 text-green-800 border-green-300",
  failed: "bg-red-100 text-red-800 border-red-300",
};

function StageRow({ label, completed, active, failed }: {
  label: string;
  completed?: boolean;
  active?: boolean;
  failed?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {completed ? (
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <Check className="h-3 w-3" />
        </span>
      ) : active ? (
        <span className="flex h-5 w-5 shrink-0 items-center justify-center">
          <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
        </span>
      ) : failed ? (
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-500">
          <X className="h-3 w-3" />
        </span>
      ) : (
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-slate-200">
          <span className="h-2 w-2 rounded-full bg-slate-200" />
        </span>
      )}
      <span className={
        completed ? "text-slate-700 font-medium" :
        active ? "text-indigo-600 font-semibold" :
        failed ? "text-red-500 font-medium" :
        "text-slate-400"
      }>
        {label}
      </span>
    </div>
  );
}

function StatusBadgeCell({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] || "bg-slate-100 text-slate-800"}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function DataIngestionPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const [previewEntry, setPreviewEntry] = useState<IntakeRegistryEntry | null>(null);
  const [previewData, setPreviewData] = useState<IntakePreviewResponse | null>(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const [deleteEntry, setDeleteEntry] = useState<IntakeRegistryEntry | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);

  const [pipelineEntries, setPipelineEntries] = useState<IntakeRegistryEntry[]>([]);
  const [isPipelineOpen, setIsPipelineOpen] = useState(false);
  const pipelineTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineEntriesRef = useRef<IntakeRegistryEntry[]>([]);

  useEffect(() => {
    pipelineEntriesRef.current = pipelineEntries;
  }, [pipelineEntries]);

  useEffect(() => {
    return () => {
      if (pipelineTimerRef.current) clearInterval(pipelineTimerRef.current);
    };
  }, []);

  useEffect(() => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  }, [page, search]);

  const retryMutation = useMutation({
    mutationFn: (entryId: string) => ingestionApi.retryExtraction(entryId),
    onSuccess: () => {
      toast.success("Document re-queued for extraction");
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
    },
    onError: (err: Error) => {
      toast.error(`Retry failed: ${err.message}`);
    },
  });

  const registryQuery = useQuery({
    queryKey: ["intake-registry", page, search],
    queryFn: ({ signal }) =>
      ingestionApi.listIntakeRegistry({
        page,
        page_size: 50,
        search: search || undefined,
      }, signal),
    refetchInterval: (query) => {
      const entries = query.state.data?.entries;
      if (!entries) return false;
      return entries.some((e) => IN_PROGRESS_STATUSES.has(e.status)) ? 3000 : false;
    },
    refetchOnWindowFocus: false,
    gcTime: 0,
  });

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => ingestionApi.uploadBatch(files, "portal"),
    onSuccess: (result: BatchUploadResponse) => {
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
      setIsUploadOpen(false);
      setSelectedFiles([]);
      setPipelineEntries(result.entries);
      setIsPipelineOpen(true);
      toast.success(`${result.accepted} of ${result.total} files uploaded — processing metadata in background`);
    },
    onError: (err: Error) => {
      toast.error(`Upload failed: ${err.message}`);
    },
  });

  const extractMutation = useMutation({
    mutationFn: (entryId: string) => ingestionApi.prepareExtraction(entryId),
    onSuccess: (result) => {
      toast.success("Opening extraction pipeline...");
      navigate(result.redirect_url);
    },
    onError: (err: Error) => {
      toast.error(`Failed to start extraction: ${err.message}`);
    },
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const valid: File[] = [];
    for (const f of Array.from(e.dataTransfer.files)) {
      const ext = "." + (f.name.split(".").pop()?.toLowerCase() ?? "");
      if (!ACCEPTED_EXTENSIONS.includes(ext)) continue;
      if (f.size > MAX_FILE_SIZE_BYTES) {
        toast.error(`${f.name} exceeds the 100 MB limit (${formatFileSize(f.size)})`);
        continue;
      }
      valid.push(f);
    }
    if (valid.length > 0) {
      setSelectedFiles((prev) => [...prev, ...valid]);
    }
  }, [toast]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const valid: File[] = [];
    for (const f of files) {
      if (f.size > MAX_FILE_SIZE_BYTES) {
        toast.error(`${f.name} exceeds the 100 MB limit (${formatFileSize(f.size)})`);
        continue;
      }
      valid.push(f);
    }
    if (valid.length > 0) {
      setSelectedFiles((prev) => [...prev, ...valid]);
    }
    e.target.value = "";
  }, [toast]);

  const handleUpload = useCallback(() => {
    if (selectedFiles.length === 0 || uploadMutation.isPending) return;
    const oversized = selectedFiles.find((f) => f.size > MAX_FILE_SIZE_BYTES);
    if (oversized) {
      toast.error(`${oversized.name} exceeds the 100 MB limit — remove it before uploading`);
      return;
    }
    uploadMutation.mutate(selectedFiles);
  }, [selectedFiles, uploadMutation]);

  const handlePreview = useCallback(
    async (entry: IntakeRegistryEntry) => {
      setPreviewEntry(entry);
      setPreviewPage(1);
      setIsPreviewOpen(true);
      setPreviewData(null);
      try {
        const data = await ingestionApi.getIntakePreview(entry.id, 1);
        setPreviewData(data);
      } catch {
        toast.error("Failed to load preview");
      }
    },
    [toast],
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteEntry) return;
    setIsDeleting(true);
    try {
      await ingestionApi.deleteIntakeEntry(deleteEntry.id);
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
      setIsDeleteOpen(false);
      setDeleteEntry(null);
      toast.success("Document permanently deleted");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setIsDeleting(false);
    }
  }, [deleteEntry, queryClient, toast]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setIsBulkDeleting(true);
    try {
      const result = await ingestionApi.bulkDeleteIntakeEntries(Array.from(selectedIds));
      queryClient.invalidateQueries({ queryKey: ["intake-registry"] });
      setSelectedIds(new Set());
      toast.success(result.message);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Bulk delete failed");
    } finally {
      setIsBulkDeleting(false);
    }
  }, [selectedIds, queryClient, toast]);

  const handleExtract = useCallback(
    (entry: IntakeRegistryEntry) => {
      extractMutation.mutate(entry.id);
    },
    [extractMutation],
  );

  const isTerminal = (s: string) => s === "ready_for_extraction" || s === "failed";

  useEffect(() => {
    if (!isPipelineOpen) return;

    if (pipelineTimerRef.current) clearInterval(pipelineTimerRef.current);

    pipelineTimerRef.current = setInterval(async () => {
      const entries = pipelineEntriesRef.current;
      if (!entries.length || entries.every((e) => isTerminal(e.status))) {
        if (pipelineTimerRef.current) {
          clearInterval(pipelineTimerRef.current);
          pipelineTimerRef.current = null;
        }
        return;
      }
      try {
        const updated = await Promise.all(
          entries.map((e) => ingestionApi.getIntakeEntry(e.id).catch(() => e)),
        );
        setPipelineEntries(updated);
      } catch {
        // Silently retry on next interval
      }
    }, 3000);

    return () => {
      if (pipelineTimerRef.current) {
        clearInterval(pipelineTimerRef.current);
        pipelineTimerRef.current = null;
      }
    };
  }, [isPipelineOpen]);

  const columns = useMemo<ColumnDef<IntakeRegistryEntry>[]>(
    () => {
      const cols: ColumnDef<IntakeRegistryEntry>[] = [];
      if (selectionMode) {
        cols.push({
          id: "select",
          header: ({ table }) => {
            const pageRows = table.getRowModel().rows;
            const allSelected = pageRows.length > 0 && pageRows.every((r) => selectedIds.has(r.original.id));
            return (
              <Checkbox
                checked={allSelected}
                onChange={() => {
                  if (allSelected) {
                    setSelectedIds((prev) => {
                      const next = new Set(prev);
                      pageRows.forEach((r) => next.delete(r.original.id));
                      return next;
                    });
                  } else {
                    setSelectedIds((prev) => {
                      const next = new Set(prev);
                      pageRows.forEach((r) => next.add(r.original.id));
                      return next;
                    });
                  }
                }}
              />
            );
          },
          cell: ({ row }) => (
            <Checkbox
              checked={selectedIds.has(row.original.id)}
              onChange={() => {
                setSelectedIds((prev) => {
                  const next = new Set(prev);
                  if (next.has(row.original.id)) {
                    next.delete(row.original.id);
                  } else {
                    next.add(row.original.id);
                  }
                  return next;
                });
              }}
            />
          ),
          size: 40,
        });
      }
      cols.push(
      {
        accessorKey: "original_filename",
        header: "Filename",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="max-w-[200px] truncate font-medium" title={row.original.original_filename}>
              {row.original.original_filename}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "id",
        header: "Document ID",
        cell: ({ row }) => (
          <code className="rounded bg-slate-100 px-1 py-0.5 text-[10px] font-mono font-semibold text-slate-800 dark:bg-slate-900 dark:text-slate-200" title={row.original.id}>
            {row.original.id}
          </code>
        ),
      },
      {
        accessorKey: "source_channel",
        header: "Channel",
        cell: ({ row }) => <Badge variant="neutral">{row.original.source_channel}</Badge>,
      },
      {
        accessorKey: "document_type",
        header: "Classification",
        cell: ({ row }) => {
          const { document_type, status } = row.original;
          if (document_type === "invoice") {
            return (
              <span className="inline-flex items-center rounded-full border border-blue-300 bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                Commercial Invoice
              </span>
            );
          }
          if (document_type === "banking_document") {
            return (
              <span className="inline-flex items-center rounded-full border border-violet-300 bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-300">
                Banking Document
              </span>
            );
          }
          const classifying = ["uploaded", "metadata_processing", "metadata_ready"].includes(status);
          if (classifying) {
            return (
              <span className="inline-flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
                <Loader2 className="h-3 w-3 animate-spin" />
                Classifying…
              </span>
            );
          }
          return <span className="text-xs text-slate-400 dark:text-slate-600">—</span>;
        },
      },
      {
        accessorKey: "language_detected",
        header: "Lang",
        cell: ({ row }) => (
          <span className="uppercase text-slate-500 dark:text-slate-400 text-xs">
            {row.original.language_detected || row.original.language || "\u2014"}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <StatusBadgeCell status={row.original.status} />,
      },
      {
        accessorKey: "is_duplicate",
        header: "Dup",
        cell: ({ row }) =>
          row.original.is_duplicate ? (
            <Badge variant="warning">Yes</Badge>
          ) : (
            <Badge variant="neutral">No</Badge>
          ),
      },
      {
        accessorKey: "file_size",
        header: "Size",
        cell: ({ row }) => (
          <span className="text-sm text-slate-500 dark:text-slate-400">{formatFileSize(row.original.file_size)}</span>
        ),
      },
      {
        accessorKey: "created_at",
        header: "Uploaded",
        cell: ({ row }) => (
          <span className="text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">
            {formatDateTime(row.original.created_at)}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => {
          const entry = row.original;
          const isReady = entry.status === "ready_for_extraction";
          const isFailed = entry.status === "failed";
          return (
            <div className="flex items-center gap-1.5">
              {isReady && (
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 px-2.5 text-xs"
                  onClick={() => handleExtract(entry)}
                  disabled={extractMutation.isPending && extractMutation.variables === entry.id}
                >
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  Extract Fields
                </Button>
              )}
              {isFailed && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 px-2.5 text-xs text-amber-600 border-amber-300 hover:bg-amber-50"
                  onClick={() => retryMutation.mutate(entry.id)}
                  disabled={retryMutation.isPending && retryMutation.variables === entry.id}
                >
                  <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${retryMutation.isPending && retryMutation.variables === entry.id ? "animate-spin" : ""}`} />
                  Retry
                </Button>
              )}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handlePreview(entry)}>
                    <Eye className="mr-2 h-4 w-4" />
                    Preview
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-red-600 focus:bg-red-50 focus:text-red-700 dark:text-red-400 dark:focus:bg-red-950/40"
                    onClick={() => {
                      setDeleteEntry(entry);
                      setIsDeleteOpen(true);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    );
      return cols;
    },
    [handlePreview, handleExtract, extractMutation.isPending, extractMutation.variables, retryMutation.isPending, retryMutation.variables, retryMutation.mutate, selectedIds, selectionMode],
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
      <PageHeader
        eyebrow="Ingestion"
        title="Data Intake"
        description="Upload, validate, deduplicate, and manage incoming documents before extraction."
        actions={
          <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Upload Files
          </Button>
        }
      />

      <div className="mb-6 grid gap-3 md:grid-cols-4">
        <MetricCard label="Total Documents" value={String(total)} tone="info" icon={Database} />
        <MetricCard
          label="Ready for Extraction"
          value={String(data.filter((e) => e.status === "ready_for_extraction").length)}
          tone="success"
          icon={Sparkles}
        />
        <MetricCard
          label="Duplicates Found"
          value={String(data.filter((e) => e.is_duplicate).length)}
          tone="warning"
          icon={AlertTriangle}
        />
        <MetricCard label="Failed" value={String(data.filter((e) => e.status === "failed").length)} tone="danger" icon={FileWarning} />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle>Intake Registry</CardTitle>
          <div className="flex items-center gap-2">
            {selectionMode ? (
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const currentIds = new Set(data.map((e) => e.id));
                    setSelectedIds((prev) => {
                      const next = new Set(currentIds);
                      if (currentIds.size === prev.size && [...currentIds].every((id) => prev.has(id))) {
                        return new Set();
                      }
                      return next;
                    });
                  }}
                >
                  {data.length > 0 && data.every((e) => selectedIds.has(e.id)) ? "Deselect All" : "Select All"}
                </Button>
                {selectedIds.size > 0 ? (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDelete}
                    disabled={isBulkDeleting}
                  >
                    {isBulkDeleting ? (
                      <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    )}
                    Delete ({selectedIds.size})
                  </Button>
                ) : null}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setSelectionMode(false); setSelectedIds(new Set()); }}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button variant="outline" size="sm" onClick={() => setSelectionMode(true)}>
                Select
              </Button>
            )}
            <div className="relative w-56">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search files..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-8 h-9 text-sm"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {registryQuery.isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : registryQuery.isError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="mb-3 h-8 w-8 text-red-400" />
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">Failed to load intake registry</p>
              <Button variant="outline" size="sm" onClick={() => registryQuery.refetch()}>
                Retry
              </Button>
            </div>
          ) : data.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileUp className="mb-3 h-10 w-10 text-slate-300 dark:text-slate-700" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">No documents ingested</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 mb-4">
                Upload your first document to get started with the intake pipeline.
              </p>
              <Button onClick={() => setIsUploadOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Document
              </Button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border dark:border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 border-b dark:bg-slate-900 dark:border-slate-800">
                    {table.getHeaderGroups().map((hg) => (
                      <tr key={hg.id}>
                        {hg.headers.map((header) => (
                          <th key={header.id} className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">
                            {header.isPlaceholder
                              ? null
                              : flexRender(header.column.columnDef.header, header.getContext())}
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {table.getRowModel().rows.map((row) => (
                      <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/60 transition-colors">
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="px-3 py-2">
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
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Extraction Loading Overlay */}
      {extractMutation.isPending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="rounded-xl border bg-white p-8 text-center shadow-2xl dark:bg-slate-900">
            <div className="mb-4 flex justify-center">
              <div className="relative h-16 w-16">
                <Loader2 className="h-16 w-16 animate-spin text-emerald-500" />
                <Sparkles className="absolute left-1/2 top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 text-emerald-600" />
              </div>
            </div>
            <p className="text-lg font-semibold text-slate-800 dark:text-slate-200">Preparing Extraction</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Setting up the Mistral OCR extraction pipeline...</p>
          </div>
        </div>
      )}

      {/* Upload Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upload Documents</DialogTitle>
            <DialogDescription>
              Drag & drop files or browse to select. Supported: PDF, JPEG, PNG, TIFF, XML, JSON (max 100 MB each).
            </DialogDescription>
          </DialogHeader>
          <div
            className={`mt-4 rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
              isDragging ? "border-indigo-500 bg-indigo-50" : "border-slate-200 bg-slate-50 hover:border-slate-300"
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto mb-3 h-10 w-10 text-slate-400" />
            <p className="text-sm font-medium text-slate-600">
              {isDragging ? "Drop files here" : "Drag & drop files or click to browse"}
            </p>
            <p className="mt-1 text-xs text-slate-400">PDF, JPEG, PNG, TIFF, XML, JSON \u2014 up to 100 MB</p>
            <Input
              type="file"
              multiple
              accept={ACCEPTED_EXTENSIONS}
              className="hidden"
              id="file-upload-input"
              onChange={handleFileSelect}
            />
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => document.getElementById("file-upload-input")?.click()}
            >
              <FileUp className="mr-2 h-4 w-4" />
              Browse Files
            </Button>
          </div>
          {selectedFiles.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium text-slate-600">
                {selectedFiles.length} file(s) selected
              </p>
              <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg border p-2">
                {selectedFiles.map((f, i) => (
                  <div key={i} className="flex items-center justify-between rounded px-2 py-1 text-sm hover:bg-slate-50">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                      <span className="truncate">{f.name}</span>
                    </div>
                    <span className="shrink-0 text-xs text-slate-400 ml-2">{formatFileSize(f.size)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelectedFiles([]);
                    setIsUploadOpen(false);
                  }}
                >
                  Cancel
                </Button>
                <Button onClick={handleUpload} disabled={uploadMutation.isPending}>
                  {uploadMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Upload {selectedFiles.length > 1 ? `All (${selectedFiles.length})` : ""}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>


      {/* Preview Dialog */}
      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              {previewEntry?.original_filename ?? "Document Preview"}
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 flex flex-col overflow-hidden">
            {previewData ? (
              <>
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-2 mb-3 text-sm text-slate-500">
                  <span>
                    {previewData.mime_type} \u2014 {formatFileSize(previewData.file_size)}
                    {previewData.total_pages > 1 && ` \u2014 ${previewData.total_pages} pages`}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={previewPage <= 1}
                      onClick={async () => {
                        const newPage = previewPage - 1;
                        setPreviewPage(newPage);
                        const data = await ingestionApi.getIntakePreview(previewEntry!.id, newPage);
                        setPreviewData(data);
                      }}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <span className="text-xs font-medium">
                      Page {previewPage} of {previewData.total_pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={previewPage >= previewData.total_pages}
                      onClick={async () => {
                        const newPage = previewPage + 1;
                        setPreviewPage(newPage);
                        const data = await ingestionApi.getIntakePreview(previewEntry!.id, newPage);
                        setPreviewData(data);
                      }}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
                <div className="flex-1 overflow-auto rounded-lg border bg-slate-50 flex items-center justify-center p-4">
                  {previewData.pages[previewPage - 1]?.image_url ? (
                    <img
                      src={previewData.pages[previewPage - 1].image_url}
                      alt={`Page ${previewPage}`}
                      className="max-w-full max-h-full object-contain shadow-md rounded"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="text-center text-slate-400">
                      <FileText className="mx-auto h-12 w-12 mb-2" />
                      <p>Preview not available for this file type</p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center flex-1">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Document?
            </DialogTitle>
            <DialogDescription>
              {deleteEntry
                ? `This action permanently removes "${deleteEntry.original_filename}" and all associated processing records (OCR, extraction, embeddings). This cannot be undone.`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete Permanently
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Upload Pipeline Progress Dialog */}
      <Dialog open={isPipelineOpen} onOpenChange={(open) => {
        if (!open) {
          setIsPipelineOpen(false);
          if (pipelineTimerRef.current) {
            clearInterval(pipelineTimerRef.current);
            pipelineTimerRef.current = null;
          }
        }
      }}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-indigo-500" />
              Upload Pipeline
            </DialogTitle>
            <DialogDescription>
              Background processing status for {pipelineEntries.length} file(s)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 max-h-[60vh] overflow-y-auto">
            {pipelineEntries.map((entry) => {
              const s = entry.status;
              const isUploaded = s === "uploaded";
              const isMetadataProcessing = s === "metadata_processing";
              const isMetadataReady = s === "metadata_ready";
              const isReady = s === "ready_for_extraction";
              const isFailed = s === "failed";

              // Stage 2 — Preprocess: active while uploaded/metadata_processing, complete when past
              const step2Complete = isMetadataReady || isReady;
              const step2Active = isUploaded || isMetadataProcessing;

              // Stage 3 — Classify: active when metadata ready and classifying, complete when doc type known
              const step3Complete = !!entry.document_type;
              const step3Active = isMetadataReady && !entry.document_type;

              // Stage 4 — Store: complete when ready_for_extraction
              const step4Complete = isReady;
              const step4Active = isMetadataReady && !!entry.document_type && !isReady;

              return (
                <div key={entry.id} className="rounded-lg border p-3">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                    <span className="text-sm font-medium truncate flex-1">{entry.original_filename}</span>
                    {isFailed && <Badge variant="danger">Failed</Badge>}
                    {isReady && <Badge variant="success">Ready</Badge>}
                    {!isFailed && !isReady && (
                      <span className="flex items-center gap-1 text-xs text-indigo-500 font-medium">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Processing
                      </span>
                    )}
                  </div>
                  <div className="space-y-1.5 pl-1">
                    <StageRow label="Upload" completed={true} />
                    <StageRow
                      label="Preprocess"
                      completed={step2Complete}
                      active={step2Active}
                      failed={isFailed && !step2Complete}
                    />
                    <StageRow
                      label={
                        entry.document_type === "invoice"
                          ? "Classify: Commercial Invoice"
                          : entry.document_type === "banking_document"
                          ? "Classify: Banking Document"
                          : "Classify"
                      }
                      completed={step3Complete}
                      active={step3Active}
                      failed={isFailed && step2Complete && !step3Complete}
                    />
                    <StageRow
                      label="Store & Ready"
                      completed={step4Complete}
                      active={step4Active}
                      failed={isFailed && step3Complete && !step4Complete}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400">
                {pipelineEntries.every((e) => isTerminal(e.status))
                  ? "All files processed"
                  : `Processing ${pipelineEntries.filter((e) => !isTerminal(e.status)).length} file(s)...`}
              </span>
              <Button variant="outline" size="sm" onClick={() => {
                setIsPipelineOpen(false);
                if (pipelineTimerRef.current) {
                  clearInterval(pipelineTimerRef.current);
                  pipelineTimerRef.current = null;
                }
              }}>
                {pipelineEntries.every((e) => isTerminal(e.status)) ? "Close" : "Minimize"}
              </Button>
            </div>
            {(() => {
              const ready = pipelineEntries.filter((e) => e.status === "ready_for_extraction");
              if (ready.length === 0) return null;
              return (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400 mb-1">
                    {ready.length} file{ready.length > 1 ? "s" : ""} ready — click to start extraction:
                  </p>
                  {ready.map((target) => (
                    <Button
                      key={target.id}
                      size="sm"
                      className="w-full bg-emerald-600 hover:bg-emerald-700 text-white justify-start"
                      onClick={() => {
                        setIsPipelineOpen(false);
                        if (pipelineTimerRef.current) {
                          clearInterval(pipelineTimerRef.current);
                          pipelineTimerRef.current = null;
                        }
                        extractMutation.mutate(target.id);
                      }}
                      disabled={extractMutation.isPending}
                    >
                      {extractMutation.isPending && extractMutation.variables === target.id ? (
                        <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Opening...</>
                      ) : (
                        <><Sparkles className="mr-2 h-3.5 w-3.5" /> Extract Fields — {target.original_filename}</>
                      )}
                    </Button>
                  ))}
                </div>
              );
            })()}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
