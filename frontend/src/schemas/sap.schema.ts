import { z } from "zod";

export const sapConnectionSchema = z.object({
  systemName: z.string().min(3, "System name is required"),
  environment: z.enum(["sandbox", "development", "quality", "uat", "production"]),
  baseUrl: z.string().url("Enter a valid SAP API base URL"),
  authType: z.enum(["oauth2_client_credentials", "basic", "certificate", "destination_service"]),
  clientId: z.string().min(2, "Client ID is required"),
  clientSecret: z.string().optional(),
  companyCode: z.string().min(2).max(8),
  apiSelection: z.array(z.enum(["journal_entry", "supplier_invoice", "customer_invoice", "asset_accounting", "bank_statement"])).min(1, "Select at least one API"),
  requestTimeoutSeconds: z.coerce.number().int().min(5).max(180),
  retryLimit: z.coerce.number().int().min(0).max(10),
  idempotencyEnabled: z.boolean(),
  certificateValidationEnabled: z.boolean(),
});

export type SapConnectionForm = z.infer<typeof sapConnectionSchema>;

export const sapMappingSchema = z.object({
  category: z.enum(["Expenses", "Income", "Assets", "Liabilities"]),
  subcategory: z.string().min(2),
  tCode: z.string().min(2),
  apiProcess: z.string().min(2),
  glAccount: z.string().min(3),
});
