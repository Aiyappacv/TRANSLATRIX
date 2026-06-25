import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/tests/msw/server";
import { accountingIntegrationApi } from "@/services/accountingIntegrationApi";
import { sapApi } from "@/services/sapApi";
import { sapConnectionSchema } from "@/schemas/sap.schema";
import { tallyExportSchema } from "@/schemas/tallyExport.schema";
import { permissions, rolePermissions } from "@/utils/permissions";
import { navGroups } from "@/app/routeConfig";

const providerCodes = ["quickbooks", "xero", "zoho_books", "tallyprime", "netsuite", "webhook_api", "workday", "servicenow"];

describe("Phase 9 integration frontend", () => {
  it("loads the provider catalog from the backend", async () => {
    server.use(http.get("/api/v1/frontend/integrations/providers", () => HttpResponse.json(providerCodes.map((code) => ({ code, name: code, type: "accounting", status: "available", authTypes: ["oauth2"], supportedActions: ["Test connection"], capabilities: { connectionTest: true } })))));
    const providers = await accountingIntegrationApi.getProviders();
    expect(providers.map((provider) => provider.code)).toEqual(expect.arrayContaining(providerCodes));
  });

  it("exposes Tally export, ERP, Workday, and ServiceNow in the company sidebar", () => {
    const integrationGroup = navGroups.find((group) => group.label === "Integrations");
    expect(integrationGroup?.items.map((item) => item.label)).toEqual(expect.arrayContaining(["Tally Export", "ERP", "Workday", "ServiceNow"]));
  });

  it("uses capability-aware backend integration details", async () => {
    server.use(http.get("/api/v1/frontend/integrations/workday", () => HttpResponse.json({ provider: { code: "workday", name: "Workday", type: "hris", status: "available", capabilities: { workerSync: true } }, settings: {}, fieldMappings: [], categoryMappings: [], accountMappings: [], taxMappings: [], logs: [], masterData: {}, summaryMetrics: [] })));
    const detail = await accountingIntegrationApi.getIntegrationDetail("workday");
    expect(detail.provider.type).toBe("hris");
    expect(detail.provider.capabilities?.workerSync).toBe(true);
    expect(tallyExportSchema.safeParse({ companyId: "company-1", companyCode: "AR01", dateFrom: "2026-06-01", dateTo: "2026-06-13", format: "xml", voucherTypes: ["purchase"], includeLedgers: true, includeCostCenters: true, includeTaxDetails: true }).success).toBe(true);
  });

  it("loads complete SAP posting records through the backend", async () => {
    server.use(http.get("/api/v1/frontend/posting/sap", () => HttpResponse.json([{ id: "sap-1", entryId: "entry-1", payload: { entry_id: "entry-1" }, accountingLines: [{ id: "line-1" }], timeline: [{ id: "event-1" }], auditEvents: [{ id: "audit-1" }], sapStatus: "ready" }])));
    const records = await sapApi.getPostingRecords();
    expect(records[0]?.payload.entry_id).toBe("entry-1");
    expect(records[0]?.timeline.length).toBeGreaterThan(0);
  });

  it("keeps SAP Posting visible and reports an unconfigured connection without false health", async () => {
    server.use(http.get("/api/v1/frontend/posting/sap/configuration-status", () => HttpResponse.json({ configured: false, tested: false, canPost: false, message: "Configure SAP and complete a successful connection test before posting." })));
    const postingGroup = navGroups.find((group) => group.label === "Posting");
    expect(postingGroup?.items.map((item) => item.label)).toContain("SAP Posting");
    const status = await sapApi.getPostingConfigurationStatus();
    expect(status.canPost).toBe(false);
    expect(status.message).toContain("Configure SAP");
  });

  it("validates a user-supplied SAP connection configuration", () => {
    const result = sapConnectionSchema.safeParse({ systemName: "SAP QA", environment: "sandbox", baseUrl: "https://sap.example.test", authType: "oauth2_client_credentials", clientId: "client", clientSecret: "secret", companyCode: "1000", apiSelection: ["journal_entry"], requestTimeoutSeconds: 60, retryLimit: 3, idempotencyEnabled: true, certificateValidationEnabled: true });
    expect(result.success).toBe(true);
  });

  it("separates posting and connector permissions by role", () => {
    expect(rolePermissions.sap_poster).toEqual(expect.arrayContaining([permissions.postingRead, permissions.postingExecute, permissions.postingRetry, permissions.postingDownload]));
    expect(rolePermissions.integration_manager).toEqual(expect.arrayContaining([permissions.integrationsRead, permissions.integrationsManage, permissions.integrationsTest, permissions.integrationsSync]));
    expect(rolePermissions.auditor).not.toContain(permissions.postingExecute);
    for (const role of ["finance_user", "reviewer", "approver"] as const) {
      expect(rolePermissions[role]).not.toContain(permissions.integrationsRead);
    }
    expect(rolePermissions.reviewer).not.toContain(permissions.reviewApprove);
    expect(rolePermissions.approver).toContain(permissions.reviewApprove);
  });
});
