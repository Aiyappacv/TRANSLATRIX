import type {
  AccountingEntryPayload,
  PostingResult,
  SapConnectionTestResult,
  SapIntegrationSettings,
  SapMappingRule,
  SapPostingRecord,
  SapPostingConfigurationStatus,
} from "@/types";
import { apiRequest } from "./apiClient";

export const sapApi = {
  getPayload: (entryId: string) =>
    apiRequest<AccountingEntryPayload>(`/posting/payload/${entryId}`),
  postEntry: (entryId: string) =>
    apiRequest<PostingResult>(`/posting/${entryId}`, { method: "POST" }),
  getMappings: () =>
    apiRequest<SapMappingRule[]>("/settings/sap-tcode-mappings"),
  getPostingResults: () => apiRequest<PostingResult[]>("/posting/results"),
  getPostingRecords: () => apiRequest<SapPostingRecord[]>("/posting/sap"),
  getPostingConfigurationStatus: () =>
    apiRequest<SapPostingConfigurationStatus>(
      "/posting/sap/configuration-status",
    ),
  getPostingRecord: (id: string) =>
    apiRequest<SapPostingRecord>(`/posting/sap/${id}`),
  executePosting: (id: string) =>
    apiRequest<SapPostingRecord>(`/posting/sap/${id}/execute`, {
      method: "POST",
    }),
  retryPosting: (id: string) =>
    apiRequest<SapPostingRecord>(`/posting/sap/${id}/retry`, {
      method: "POST",
    }),
  getSettings: () =>
    apiRequest<SapIntegrationSettings>("/integrations/sap/settings"),
  saveSettings: (payload: SapIntegrationSettings) =>
    apiRequest<SapIntegrationSettings>("/integrations/sap/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testConnection: (payload?: Partial<SapIntegrationSettings>) =>
    apiRequest<SapConnectionTestResult>("/integrations/sap/test", {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    }),
  suggestMapping: async (category: string, subcategory: string) => {
    const mappings = await apiRequest<SapMappingRule[]>(
      "/settings/mapping-rules",
    );
    return (
      mappings.find(
        (rule) =>
          rule.category === category &&
          rule.subcategory.toLowerCase() === subcategory.toLowerCase(),
      ) ??
      mappings.find((rule) => rule.category === category) ??
      null
    );
  },
};
