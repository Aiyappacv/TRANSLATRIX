import type { ExtractionJson, IngestedFile } from "@/types";
import { apiDownload, apiRequest } from "./apiClient";

export const fileApi = {
  getFiles: () => apiRequest<IngestedFile[]>("/files"),
  getFile: (id: string) => apiRequest<IngestedFile>(`/files/${id}`),
  uploadLocalFile: (file: File) => {
    const data = new FormData();
    data.append("file", file);
    return apiRequest<IngestedFile>("/files/upload", { method: "POST", body: data });
  },
  processFile: (id: string) => apiRequest<IngestedFile>(`/files/${id}/process`, { method: "POST" }),
  downloadFile: (id: string, fileName: string) => apiDownload(`/files/${id}/download`, fileName),
  deleteFile: (id: string) => apiRequest<void>(`/files/${id}`, { method: "DELETE" }),
  getPreviewUrl: (id: string) => apiRequest<{ url: string }>(`/files/${id}/preview`),
  retryOcr: (id: string) => apiRequest<{ id: string; status: string }>(`/files/${id}/ocr/retry`, { method: "POST" }),
  runCloudOcrFallback: (id: string) => apiRequest<{ id: string; status: string; provider: string }>(`/files/${id}/ocr/cloud-fallback`, { method: "POST" }),
  saveTableCorrections: (id: string, tableId: string, rows: string[][]) => apiRequest<{ id: string; tableId: string; status: string }>(`/files/${id}/tables/${tableId}`, { method: "PATCH", body: JSON.stringify({ rows }) }),
  retryProcessingStep: (id: string, step: string) => apiRequest<{ id: string; step: string; status: string }>(`/files/${id}/steps/${step}/retry`, { method: "POST" }),
  getExtractionJson: (id: string) => apiRequest<ExtractionJson>(`/files/${id}/json`),
  downloadExtractionJson: (id: string, fileName: string) => apiDownload(`/files/${id}/download-json`, fileName),
  downloadExtractionSummary: (id: string, fileName: string) => apiDownload(`/files/${id}/download-extraction-summary`, fileName),
};
