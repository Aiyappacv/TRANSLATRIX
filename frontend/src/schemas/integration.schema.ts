import { z } from "zod";

export const integrationConfigSchema = z.object({
  providerCode: z.string(),
  displayName: z.string().min(3),
  environment: z.enum(["sandbox", "development", "uat", "production", "local"]),
  authType: z.enum(["oauth2", "client_credentials", "api_key", "basic", "certificate", "sftp_key", "none"]),
  baseUrl: z.string().url().or(z.literal("")).optional(),
  companyCode: z.string().optional(),
  tenantId: z.string().optional(),
  clientId: z.string().optional(),
  clientSecret: z.string().optional(),
  apiKey: z.string().optional(),
  webhookUrl: z.string().url().or(z.literal("")).optional(),
  customValues: z.record(z.string()),
  enabled: z.boolean(),
  autoSyncEnabled: z.boolean(),
  syncFrequency: z.enum(["manual", "hourly", "daily", "weekly"]),
});

export type IntegrationConfigForm = z.infer<typeof integrationConfigSchema>;
