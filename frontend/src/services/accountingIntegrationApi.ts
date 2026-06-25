import type {
  CustomConnectorInput,
  IntegrationConnectionSettings,
  IntegrationDetail,
  IntegrationProvider,
  IntegrationTestResult,
  MasterDataSyncResult,
} from "@/types";
import { apiRequest } from "./apiClient";

export const accountingIntegrationApi = {
  getProviders: () => apiRequest<IntegrationProvider[]>("/integrations/providers"),
  getProvider: (providerCode: string) => apiRequest<IntegrationProvider>(`/integrations/providers/${providerCode}`),
  getIntegrationDetail: (providerCode: string) => apiRequest<IntegrationDetail>(`/integrations/${providerCode}`),
  registerCustomConnector: (input: CustomConnectorInput) => apiRequest<IntegrationDetail>("/integrations/custom", { method: "POST", body: JSON.stringify(input) }),
  saveConnectionSettings: (providerCode: string, settings: IntegrationConnectionSettings) => apiRequest<IntegrationDetail>(`/integrations/${providerCode}/settings`, { method: "PUT", body: JSON.stringify(settings) }),
  saveIntegrationDetail: (providerCode: string, detail: IntegrationDetail) => apiRequest<IntegrationDetail>(`/integrations/${providerCode}`, { method: "PUT", body: JSON.stringify(detail) }),
  testProvider: (providerCode: string) => apiRequest<IntegrationTestResult>(`/integrations/${providerCode}/test`, { method: "POST" }),
  syncMasterData: (providerCode: string) => apiRequest<MasterDataSyncResult>(`/integrations/${providerCode}/sync-master-data`, { method: "POST" }),
};
