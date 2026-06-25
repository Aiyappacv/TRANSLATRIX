import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { monitoringApi } from "@/services/monitoringApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { LogTable } from "@/components/common/LogTable";
import { FilterBar } from "@/components/common/FilterBar";
import { Input } from "@/components/ui/input";

export function ProcessingLogsPage() {
  const query = useQuery({ queryKey: ["monitoring", "processing-logs"], queryFn: monitoringApi.getProcessingLogs });
  const [stage, setStage] = useState(""); const [level, setLevel] = useState(""); const [entity, setEntity] = useState("");
  const rows = useMemo(() => (query.data ?? []).filter((row) => (!stage || row.stage.includes(stage.toLowerCase())) && (!level || row.level.includes(level.toLowerCase())) && (!entity || [row.jobId, row.batchId, row.fileId, row.requestId].filter(Boolean).some((value) => value!.toLowerCase().includes(entity.toLowerCase())))), [entity, level, query.data, stage]);
  return <div className="space-y-6"><PageHeader eyebrow="Phase 13 · Monitoring" title="Processing logs" description="Worker jobs, batches, files, OCR, translation, classification, validation, and SAP posting timelines." />
    <FilterBar><Input placeholder="Stage" value={stage} onChange={(event) => setStage(event.target.value)} /><Input placeholder="Level" value={level} onChange={(event) => setLevel(event.target.value)} /><Input className="md:col-span-2" placeholder="Job, batch, file, or request ID" value={entity} onChange={(event) => setEntity(event.target.value)} /></FilterBar>
    {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState title="Processing logs unavailable" description="Worker logs could not be loaded." onRetry={() => query.refetch()} /> : <LogTable logs={rows} />}
  </div>;
}
