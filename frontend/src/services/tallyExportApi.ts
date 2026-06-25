import type { CreateTallyExportRequest, TallyExportDownload, TallyExportJob } from "@/types";
import { apiDownload, apiRequest } from "./apiClient";

export const tallyExportApi = {
  listExports: () => apiRequest<TallyExportJob[]>("/integrations/tallyprime/exports"),
  createExport: (payload: CreateTallyExportRequest) => apiRequest<TallyExportJob>("/integrations/tallyprime/exports", { method: "POST", body: JSON.stringify(payload) }),
  retryExport: (exportId: string) => apiRequest<TallyExportJob>(`/integrations/tallyprime/exports/${exportId}/retry`, { method: "POST" }),
  getDownload: (exportId: string) => apiRequest<TallyExportDownload>(`/integrations/tallyprime/exports/${exportId}/download`),
  downloadExport: async (exportId: string) => {
    const metadata = await apiRequest<TallyExportDownload>(`/integrations/tallyprime/exports/${exportId}/download`);
    await apiDownload(metadata.downloadUrl, metadata.fileName);
    return metadata;
  },
};
