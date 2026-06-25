import type { DocumentRegistryDetail, DocumentRegistryListResponse, IngestedFile } from "@/types";
import { apiDownload, apiRequest } from "./apiClient";

export const documentRegistryApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; status?: string; ocr_engine?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    if (params?.ocr_engine) query.set("ocr_engine", params.ocr_engine);
    const qs = query.toString();
    return apiRequest<DocumentRegistryListResponse>(`/document-registry${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiRequest<DocumentRegistryDetail>(`/document-registry/${id}`),
  reprocess: (id: string) => apiRequest<IngestedFile>(`/document-registry/${id}/reprocess`, { method: "POST" }),
  delete: (id: string) => apiRequest<void>(`/document-registry/${id}`, { method: "DELETE" }),
  exportCsv: (params?: { search?: string; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    const qs = query.toString();
    return apiDownload(`/document-registry/export/csv${qs ? `?${qs}` : ""}`, "document_registry.csv");
  },
  exportXlsx: (params?: { search?: string; status?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    const qs = query.toString();
    return apiDownload(`/document-registry/export/xlsx${qs ? `?${qs}` : ""}`, "document_registry.xlsx");
  },
};
