import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/tests/msw/server";
import { superAdminApi } from "@/services/superAdminApi";
import { superAdminNavGroups } from "@/app/superAdminRouteConfig";
import { permissions, rolePermissions } from "@/utils/permissions";

const requiredRoutes = ["/super-admin/dashboard", "/super-admin/companies", "/super-admin/company-onboarding", "/super-admin/subscriptions", "/super-admin/billing", "/super-admin/integrations", "/super-admin/system-health", "/super-admin/job-queues", "/super-admin/error-center", "/super-admin/usage-analytics", "/super-admin/audit-logs", "/super-admin/support", "/super-admin/settings"];

describe("Phase 10 Super Admin platform", () => {
  it("registers every requested Super Admin navigation route", () => {
    const routes = superAdminNavGroups.flatMap((group) => group.items.map((item) => item.path));
    expect(routes).toEqual(expect.arrayContaining(requiredRoutes));
  });

  it("loads platform KPIs from the backend", async () => {
    server.use(http.get("/api/v1/frontend/super-admin/dashboard", () => HttpResponse.json({ kpis: [{ key: "total_companies", label: "Companies", value: 1 }], usageTrend: [], statusDistribution: [], topCompanies: [], recentErrors: [], queueSnapshot: [], providerSnapshot: [] })));
    const dashboard = await superAdminApi.getDashboard();
    expect(dashboard.kpis.map((item) => item.key)).toContain("total_companies");
  });

  it("loads company management records from the backend", async () => {
    server.use(http.get("/api/v1/frontend/super-admin/companies", () => HttpResponse.json([{ id: "c1", tenantId: "t1", legalName: "Development Company", status: "active", adminEmail: "admin@example.test", lastActivityAt: new Date().toISOString(), storageUsedGb: 0 }])));
    const companies = await superAdminApi.getCompanies();
    expect(companies[0]?.tenantId).toBe("t1");
  });

  it("loads and approves pending company registrations with an activation path", async () => {
    server.use(
      http.get("/api/v1/frontend/super-admin/registration-requests", () => HttpResponse.json([{ id: "registration-1", companyId: "company-1", companyName: "Pending Company", adminEmail: "admin@pending.test", country: "India", industry: "Finance", status: "pending", createdAt: new Date().toISOString() }])),
      http.post("/api/v1/frontend/super-admin/registration-requests/registration-1/approve", () => HttpResponse.json({ request: { id: "registration-1", companyId: "company-1", companyName: "Pending Company", adminEmail: "admin@pending.test", country: "India", industry: "Finance", status: "approved", createdAt: new Date().toISOString() }, company: { id: "company-1", tenantId: "tenant-1", companyName: "Pending Company", country: "India", industry: "Finance", plan: "Starter", status: "active", users: 1, filesProcessed: 0, entriesProcessed: 0, sapPostings: 0, accountingPostings: 0, storageUsedGb: 0, createdAt: new Date().toISOString(), lastActivityAt: new Date().toISOString(), adminEmail: "admin@pending.test", billingStatus: "current", mfaCoverage: 0, ipRestrictionsEnabled: false }, activationPath: "/auth/reset-password?token=one-time-token" })),
    );
    const requests = await superAdminApi.getRegistrationRequests();
    expect(requests[0]?.status).toBe("pending");
    const approval = await superAdminApi.approveRegistrationRequest("registration-1");
    expect(approval.request.status).toBe("approved");
    expect(approval.company.status).toBe("active");
    expect(approval.activationPath).toContain("token=");
  });

  it("loads provider and operational telemetry", async () => {
    server.use(
      http.get("/api/v1/frontend/super-admin/integrations", () => HttpResponse.json([{ code: "sap", name: "SAP S/4HANA", status: "operational" }])),
      http.get("/api/v1/frontend/super-admin/system-health", () => HttpResponse.json([{ id: "api", name: "API", status: "healthy", latencyMs: 1, uptime: 100, lastCheckedAt: new Date().toISOString() }])),
      http.get("/api/v1/frontend/super-admin/job-queues", () => HttpResponse.json([{ id: "ocr", name: "OCR", type: "ocr", waiting: 0, active: 0, failed: 0, completedToday: 0, throughputPerMinute: 0, oldestJobAgeSeconds: 0, status: "healthy" }])),
    );
    expect((await superAdminApi.getProviders()).length).toBeGreaterThan(0);
    expect((await superAdminApi.getSystemHealth()).length).toBeGreaterThan(0);
    expect((await superAdminApi.getJobQueues())[0]?.type).toBe("ocr");
  });

  it("keeps platform permissions exclusive to the Super Admin role", () => {
    expect(rolePermissions.spectra_super_admin).toEqual(expect.arrayContaining([permissions.platformDashboardRead, permissions.platformCompaniesManage, permissions.platformTenantView, permissions.platformBillingManage, permissions.platformHealthRead, permissions.platformAuditRead]));
    expect(rolePermissions.company_admin).not.toContain(permissions.platformDashboardRead);
    expect(rolePermissions.integration_manager).not.toContain(permissions.platformCompaniesManage);
  });
});
