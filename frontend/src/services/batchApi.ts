import type { IngestionBatch } from "@/types";
import { apiRequest } from "./apiClient";

export const batchApi = {
  getBatches: () => apiRequest<IngestionBatch[]>("/batches"),
  getBatch: (id: string) => apiRequest<IngestionBatch>(`/batches/${id}`),
  retryFailedBatches: () => apiRequest<{ retried: number; status: string }>("/batches/retry-failed", { method: "POST" }),
  retryBatch: (id: string) => apiRequest<{ id: string; status: string }>(`/batches/${id}/retry`, { method: "POST" }),
};
