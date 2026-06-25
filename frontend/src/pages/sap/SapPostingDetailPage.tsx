import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  RotateCcw,
  Send,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { sapApi } from "@/services/sapApi";
import { AuditTimeline } from "@/components/common/AuditTimeline";
import { ErrorState } from "@/components/common/ErrorState";
import { JsonPayloadEditor } from "@/components/common/JsonPayloadEditor";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatDateTime } from "@/utils/formatters";
import { permissions } from "@/utils/permissions";

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

function SummaryItem({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <div className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </div>
    </div>
  );
}

export function SapPostingDetailPage() {
  const { postingId = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const posting = useQuery({
    queryKey: ["sap-posting", postingId],
    queryFn: () => sapApi.getPostingRecord(postingId),
    enabled: Boolean(postingId),
  });
  const configuration = useQuery({
    queryKey: ["sap-posting-configuration"],
    queryFn: sapApi.getPostingConfigurationStatus,
  });
  const execute = useMutation({
    mutationFn: ({ id, retry }: { id: string; retry: boolean }) =>
      retry ? sapApi.retryPosting(id) : sapApi.executePosting(id),
    onSuccess: (record) => {
      queryClient.setQueryData(["sap-posting", postingId], record);
      queryClient.invalidateQueries({ queryKey: ["sap-postings"] });
      toast.success(
        "SAP document created",
        `Document ${record.sapDocumentNumber} was posted successfully.`,
      );
    },
    onError: (error) =>
      toast.error(
        "Posting failed",
        error instanceof Error
          ? error.message
          : "Unexpected SAP connector error.",
      ),
  });

  if (posting.isLoading)
    return <LoadingState label="Loading SAP posting detail..." />;
  if (posting.isError || !posting.data)
    return (
      <ErrorState
        title="Posting record unavailable"
        description={
          posting.error instanceof Error
            ? posting.error.message
            : "The requested posting record could not be found."
        }
        onRetry={() => posting.refetch()}
      />
    );

  const record = posting.data;
  const sapPostingEnabled = configuration.data?.canPost === true;
  const canPost = record.sapStatus === "ready";
  const canRetry = record.sapStatus === "failed";

  return (
    <>
      <PageHeader
        eyebrow="SAP posting detail"
        title={record.entryId}
        description={`${record.sapProcess} · ${record.companyCode} · ${formatCurrency(record.amount, record.currency)}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            {record.response ? (
              <Can permissions={[permissions.postingDownload]}>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadJson(
                      `${record.entryId}-sap-response.json`,
                      record.response,
                    )
                  }
                >
                  <Download className="h-4 w-4" />
                  Download response
                </Button>
              </Can>
            ) : null}
            {canPost ? (
              <Can permissions={[permissions.postingExecute]}>
                <Button
                  disabled={execute.isPending || !sapPostingEnabled}
                  onClick={() =>
                    execute.mutate({ id: record.id, retry: false })
                  }
                >
                  <Send className="h-4 w-4" />
                  Post to SAP
                </Button>
              </Can>
            ) : null}
            {canRetry ? (
              <Can permissions={[permissions.postingRetry]}>
                <Button
                  disabled={execute.isPending || !sapPostingEnabled}
                  onClick={() => execute.mutate({ id: record.id, retry: true })}
                >
                  <RotateCcw className="h-4 w-4" />
                  Retry posting
                </Button>
              </Can>
            ) : null}
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

      <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryItem
          label="SAP status"
          value={<SapPostingStatusBadge status={record.sapStatus} />}
        />
        <SummaryItem
          label="Approval status"
          value={
            <Badge
              variant={
                record.approvalStatus === "approved" ? "success" : "warning"
              }
            >
              {record.approvalStatus.replaceAll("_", " ")}
            </Badge>
          }
        />
        <SummaryItem
          label="SAP document"
          value={
            record.sapDocumentNumber ? (
              <span className="font-mono">
                {record.sapDocumentNumber} / {record.fiscalYear}
              </span>
            ) : (
              "Not created"
            )
          }
        />
        <SummaryItem
          label="Posting attempts"
          value={`${record.attempts}${record.lastAttemptAt ? ` · ${formatDateTime(record.lastAttemptAt)}` : ""}`}
        />
      </div>

      {record.errorMessage ? (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5" />
            <div>
              <p className="font-semibold">{record.errorCode}</p>
              <p className="mt-1">{record.errorMessage}</p>
            </div>
          </div>
        </div>
      ) : null}

      <Tabs defaultValue="summary">
        <div className="overflow-x-auto pb-1">
          <TabsList className="min-w-max">
            <TabsTrigger value="summary">Entry summary</TabsTrigger>
            <TabsTrigger value="accounting">Accounting entry</TabsTrigger>
            <TabsTrigger value="payload">SAP payload JSON</TabsTrigger>
            <TabsTrigger value="response">SAP response</TabsTrigger>
            <TabsTrigger value="timeline">Posting timeline</TabsTrigger>
            <TabsTrigger value="audit">Audit</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="summary">
          <div className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
            <Card>
              <CardHeader>
                <CardTitle>Approved entry</CardTitle>
                <CardDescription>
                  The posting payload is derived from this locked source record.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <SummaryItem
                  label="Category"
                  value={`${record.category} · ${record.sourceEntry?.subcategory ?? "—"}`}
                />
                <SummaryItem
                  label="SAP T-Code"
                  value={<Badge variant="brand">{record.sapTCode}</Badge>}
                />
                <SummaryItem
                  label="Reference"
                  value={record.sourceEntry?.reference ?? record.entryId}
                />
                <SummaryItem
                  label="Source file"
                  value={
                    record.sourceEntry ? (
                      <Link
                        className="text-primary hover:underline"
                        to={`/app/files/${record.sourceEntry.fileId}`}
                      >
                        {record.sourceEntry.sourceFile}
                      </Link>
                    ) : (
                      "—"
                    )
                  }
                />
                <SummaryItem
                  label="Description"
                  value={record.sourceEntry?.englishDescription ?? "—"}
                />
                <SummaryItem
                  label="Approved by"
                  value={`${record.approvedBy ?? "—"}${record.approvedAt ? ` · ${formatDateTime(record.approvedAt)}` : ""}`}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Posting controls</CardTitle>
                <CardDescription>
                  Production safeguards applied before remote submission.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {[
                  "Approval lock verified",
                  "Debit and credit totals balanced",
                  "Idempotency key assigned",
                  "Company code and API route validated",
                  "Payload hash stored in audit trail",
                ].map((item) => (
                  <div
                    key={item}
                    className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    {item}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="accounting">
          <Card>
            <CardHeader>
              <CardTitle>Debit and credit lines</CardTitle>
              <CardDescription>
                Read-only accounting entry approved for posting.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900">
                    <tr>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">GL account</th>
                      <th className="px-4 py-3">Account name</th>
                      <th className="px-4 py-3">Cost center</th>
                      <th className="px-4 py-3">Tax code</th>
                      <th className="px-4 py-3 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {record.accountingLines.map((line) => (
                      <tr
                        key={line.id}
                        className="border-t border-slate-100 dark:border-slate-800"
                      >
                        <td className="px-4 py-3">
                          <Badge
                            variant={line.type === "debit" ? "info" : "success"}
                          >
                            {line.type}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          {line.glAccount}
                        </td>
                        <td className="px-4 py-3">{line.accountName}</td>
                        <td className="px-4 py-3">{line.costCenter ?? "—"}</td>
                        <td className="px-4 py-3">{line.taxCode ?? "—"}</td>
                        <td className="px-4 py-3 text-right font-semibold tabular-nums">
                          {formatCurrency(line.amount, line.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payload">
          <JsonPayloadEditor
            title="SAP payload JSON"
            value={record.payload}
            height={620}
          />
        </TabsContent>
        <TabsContent value="response">
          {record.response ? (
            <JsonPayloadEditor
              title="SAP response JSON"
              value={record.response}
              height={620}
            />
          ) : (
            <Card>
              <CardContent className="flex min-h-72 items-center justify-center text-sm text-slate-500">
                No SAP response is available until a posting attempt is made.
              </CardContent>
            </Card>
          )}
        </TabsContent>
        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>Posting timeline</CardTitle>
              <CardDescription>
                End-to-end state transitions for this posting record.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {record.timeline.map((event) => (
                <div
                  key={event.id}
                  className="flex gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-800"
                >
                  <div
                    className={`mt-1 h-3 w-3 shrink-0 rounded-full ${event.status === "failed" ? "bg-red-500" : event.status === "current" ? "bg-amber-500" : "bg-emerald-500"}`}
                  />
                  <div className="flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="font-semibold">{event.title}</p>
                      <span className="text-xs text-slate-500">
                        {formatDateTime(event.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                      {event.description}
                    </p>
                    <p className="mt-2 text-xs font-medium text-slate-400">
                      {event.actor}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="audit">
          <AuditTimeline events={record.auditEvents} />
        </TabsContent>
      </Tabs>
    </>
  );
}
