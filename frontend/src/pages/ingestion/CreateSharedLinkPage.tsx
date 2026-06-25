import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, CheckCircle2, FileSearch, Link2, Loader2, ShieldCheck } from "lucide-react";
import type { LinkValidationResult } from "@/types";
import { ingestionApi } from "@/services/ingestionApi";
import { sharedLinkAuthTypes, sharedLinkScheduleModes, sharedLinkSourceTypes, sharedLinkSchema, type SharedLinkInput } from "@/schemas/ingestion.schema";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { FileDropzone } from "@/components/common/FileDropzone";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ColumnDef } from "@tanstack/react-table";
import type { FileDiscoveryItem } from "@/types";
import { formatDateTime, formatNumber } from "@/utils/formatters";

const initialForm: SharedLinkInput = {
  clientName: "",
  sourceType: "Local Upload",
  name: "",
  url: "",
  authenticationType: "None",
  folderPath: "",
  fileFilters: "",
  schedule: "Manual",
  defaultCompanyCode: "",
  defaultCurrency: "",
  defaultReviewerGroup: "",
  defaultAccountingIntegration: "",
};

const fileColumns: ColumnDef<FileDiscoveryItem>[] = [
  { accessorKey: "fileName", header: "File", cell: ({ row }) => <div><p className="font-medium">{row.original.fileName}</p><p className="text-xs text-slate-500">{row.original.path}</p></div> },
  { accessorKey: "mimeType", header: "Type" },
  { accessorKey: "sizeBytes", header: "Size", cell: ({ row }) => `${formatNumber(row.original.sizeBytes / 1024)} KB` },
  { accessorKey: "status", header: "Status", cell: ({ row }) => row.original.status === "supported" ? <Badge variant="success">Supported</Badge> : <Badge variant="warning">{row.original.status}</Badge> },
  { accessorKey: "discoveredAt", header: "Discovered", cell: ({ row }) => formatDateTime(row.original.discoveredAt) },
];

export function CreateSharedLinkPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<SharedLinkInput>(initialForm);
  const [validation, setValidation] = useState<LinkValidationResult | null>(null);
  const [localFiles, setLocalFiles] = useState<File[]>([]);

  const canCreate = validation?.accessible && validation.supportedFilesCount > 0;

  const validateMutation = useMutation({
    mutationFn: ingestionApi.validateSharedLink,
    onSuccess: (result) => {
      setValidation(result);
      if (result.accessible) toast.success(`Link validated: ${result.supportedFilesCount} supported files found`);
      else toast.error("The source could not be accessed with the supplied configuration");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Link validation failed"),
  });

  const createMutation = useMutation({
    mutationFn: ingestionApi.createSharedLink,
    onSuccess: (created) => {
      toast.success("Shared source created");
      navigate(`/app/ingestion/shared-links/${created.id}`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Unable to create shared source"),
  });

  const errors = useMemo(() => {
    const localUrl = form.sourceType === "Local Upload" && localFiles.length ? `local://${localFiles.map((file) => file.name).join(",")}` : form.url;
    const parsed = sharedLinkSchema.safeParse({ ...form, url: localUrl, provider: form.sourceType });
    const issues = parsed.success ? [] : parsed.error.issues.map((issue) => issue.message);
    if (form.sourceType === "Local Upload" && !localFiles.length) issues.push("Select at least one local file");
    return issues;
  }, [form, localFiles]);

  const update = (key: keyof SharedLinkInput, value: string) => {
    setForm((current) => ({ ...current, [key]: value, ...(key === "sourceType" && value === "Local Upload" ? { url: "" } : {}) }));
    setValidation(null);
  };

  const handleValidate = () => {
    const localUrl = form.sourceType === "Local Upload" && localFiles.length ? `local://${localFiles.map((file) => file.name).join(",")}` : form.url;
    const parsed = sharedLinkSchema.safeParse({ ...form, url: localUrl, provider: form.sourceType });
    if (!parsed.success || (form.sourceType === "Local Upload" && !localFiles.length)) {
      toast.error(form.sourceType === "Local Upload" && !localFiles.length ? "Select at least one local file" : parsed.success ? "Complete all required source fields" : (parsed.error.issues[0]?.message ?? "Complete all required source fields"));
      return;
    }
    validateMutation.mutate(parsed.data);
  };
  const handleCreate = () => {
    const localUrl = form.sourceType === "Local Upload" && localFiles.length ? `local://${localFiles.map((file) => file.name).join(",")}` : form.url;
    const parsed = sharedLinkSchema.safeParse({ ...form, url: localUrl, provider: form.sourceType });
    if (!parsed.success || !canCreate) {
      toast.error("Validate an accessible source with supported files before creating it");
      return;
    }
    createMutation.mutate(parsed.data);
  };

  return (
    <>
      <PageHeader
        eyebrow="Ingestion"
        title="Create shared link"
        description="Register a client source, validate access, discover files, and convert the link into a processable batch source."
        actions={<Button asChild variant="outline"><Link to="/app/ingestion/shared-links">Back to shared links</Link></Button>}
      />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Link2 className="h-5 w-5 text-primary" />Source configuration</CardTitle>
            <CardDescription>All required Phase 5 fields are captured before validation.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Client name</Label>
                <Input value={form.clientName} onChange={(event) => update("clientName", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Source type</Label>
                <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={form.sourceType} onChange={(event) => update("sourceType", event.target.value)}>
                  {sharedLinkSourceTypes.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Source display name</Label>
                <Input value={form.name} onChange={(event) => update("name", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Authentication type</Label>
                <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={form.authenticationType} onChange={(event) => update("authenticationType", event.target.value)}>
                  {sharedLinkAuthTypes.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
              {form.sourceType === "Local Upload" ? (
                <div className="space-y-2 md:col-span-2">
                  <Label>Local files</Label>
                  <FileDropzone accept=".pdf,.png,.jpg,.jpeg,.webp,.csv,.xlsx,.xls,.docx" onFiles={(files) => { setLocalFiles(files); setValidation(null); }} />
                </div>
              ) : (
                <div className="space-y-2 md:col-span-2">
                  <Label>Shared URL / endpoint</Label>
                  <Input value={form.url} onChange={(event) => update("url", event.target.value)} placeholder="https://, sftp://, s3://, azure://, or manual URL" />
                </div>
              )}
              <div className="space-y-2">
                <Label>Folder path</Label>
                <Input value={form.folderPath} onChange={(event) => update("folderPath", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>File filters</Label>
                <Input value={form.fileFilters} onChange={(event) => update("fileFilters", event.target.value)} placeholder="*.pdf, *.xlsx, *.jpg" />
              </div>
              <div className="space-y-2">
                <Label>Schedule mode</Label>
                <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={form.schedule} onChange={(event) => update("schedule", event.target.value)}>
                  {sharedLinkScheduleModes.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Default company code</Label>
                <Input value={form.defaultCompanyCode} onChange={(event) => update("defaultCompanyCode", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Default currency</Label>
                <Input value={form.defaultCurrency} maxLength={3} onChange={(event) => update("defaultCurrency", event.target.value.toUpperCase())} />
              </div>
              <div className="space-y-2">
                <Label>Default reviewer group</Label>
                <Input value={form.defaultReviewerGroup} onChange={(event) => update("defaultReviewerGroup", event.target.value)} />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label>Default accounting integration</Label>
                <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={form.defaultAccountingIntegration} onChange={(event) => update("defaultAccountingIntegration", event.target.value)}>
                  {["SAP S/4HANA", "QuickBooks", "Xero", "Zoho Books", "TallyPrime", "Sage", "NetSuite", "Manual JSON export"].map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
            </div>

            {errors.length ? <div className="mt-4 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">Resolve these fields before validating: {errors.join(" · ")}</div> : null}

            <div className="mt-6 flex flex-wrap gap-3">
              <Button disabled={validateMutation.isPending || errors.length > 0} onClick={handleValidate} variant="outline">
                {validateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
                Validate link
              </Button>
              <Button disabled={!canCreate || createMutation.isPending} onClick={handleCreate}>
                {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                Create source
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Link validation UI</CardTitle>
            <CardDescription>Shows access state, file counts, estimated time, and security warnings.</CardDescription>
          </CardHeader>
          <CardContent>
            {!validation ? (
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">Run validation to discover files and security warnings.</div>
            ) : (
              <div className="space-y-4">
                <div className={`rounded-2xl border p-4 ${validation.accessible ? "border-success/30 bg-success/10" : "border-danger/30 bg-danger/10"}`}>
                  <div className="flex items-center gap-3">
                    {validation.accessible ? <CheckCircle2 className="h-5 w-5 text-success" /> : <AlertTriangle className="h-5 w-5 text-danger" />}
                    <div>
                      <p className="font-semibold">{validation.accessible ? "Accessible" : "Not accessible"}</p>
                      <p className="text-xs text-slate-500">Connector responded in {validation.latencyMs}ms</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricCard label="Files found" value={String(validation.filesFound)} tone="info" icon={FileSearch} />
                  <MetricCard label="Supported files" value={String(validation.supportedFilesCount)} tone="success" icon={CheckCircle2} />
                  <MetricCard label="Unsupported files" value={String(validation.unsupportedFilesCount)} tone={validation.unsupportedFilesCount ? "warning" : "success"} icon={AlertTriangle} />
                  <MetricCard label="Estimated time" value={validation.estimatedProcessingTime} tone="neutral" icon={Loader2} />
                </div>

                {validation.securityWarning ? (
                  <div className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
                    <div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4" /><span>{validation.securityWarning}</span></div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-success/30 bg-success/10 p-4 text-sm text-success">No security warning detected.</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {validation ? (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>File discovery table</CardTitle>
            <CardDescription>Preview of files that will become the first processable ingestion batch.</CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable columns={fileColumns} data={validation.discoveredFiles} searchPlaceholder="Search discovered files..." />
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}
