import type { IntegrationDetail, IntegrationProvider, SapIntegrationSettings, SapPostingRecord } from "@/types";

// Production-clean integration fixtures. Provider and connection records must come from the backend.
export const phase9IntegrationProviders: IntegrationProvider[] = [];
export const phase9IntegrationDetails: Record<string, IntegrationDetail> = {};
export const phase9SapSettings: SapIntegrationSettings = {
  id: "",
  systemName: "",
  environment: "production",
  baseUrl: "",
  authType: "oauth2_client_credentials",
  clientId: "",
  companyCode: "",
  apiSelection: [],
  requestTimeoutSeconds: 30,
  retryLimit: 0,
  idempotencyEnabled: true,
  certificateValidationEnabled: true,
  status: "not_configured",
  updatedAt: "",
};
export const phase9SapPostings: SapPostingRecord[] = [];
