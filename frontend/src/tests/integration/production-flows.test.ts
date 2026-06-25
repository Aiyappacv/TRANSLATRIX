import { describe, expect, it } from "vitest";
import { authApi } from "@/services/authApi";
import { companyApi } from "@/services/companyApi";
import { ingestionApi } from "@/services/ingestionApi";
import { batchApi } from "@/services/batchApi";
import { reviewApi } from "@/services/reviewApi";
import { sapApi } from "@/services/sapApi";
import { superAdminApi } from "@/services/superAdminApi";
import { dashboardRolePaths, getDashboardRole } from "@/utils/dashboardRoles";
import { apiRequest } from "@/services/apiClient";
import type { RegisterCompanyInput } from "@/schemas/company.schema";
import type { SharedLinkInput } from "@/schemas/ingestion.schema";
import { isAuthSession } from "@/types";

const actor = { id: "backend_test_approver", name: "Backend Test Approver", role: "Approver" };
const backendDescribe = process.env.RUN_BACKEND_INTEGRATION_TESTS === "true" ? describe : describe.skip;

backendDescribe("Production-critical backend workflows", () => {
  it("logs in a configured user and returns a scoped session", async () => {
    const email = process.env.BACKEND_TEST_USER_EMAIL;
    const password = process.env.BACKEND_TEST_USER_PASSWORD;
    if (!email || !password) throw new Error("Set BACKEND_TEST_USER_EMAIL and BACKEND_TEST_USER_PASSWORD.");

    const session = await authApi.login({ email, password });
    if (!isAuthSession(session)) throw new Error("The integration account requires MFA; complete MFA before running this test.");
    expect(session.accessToken).toEqual(expect.any(String));
    expect(session.user.email.toLowerCase()).toBe(email.toLowerCase());
    expect(session.user.roles.length).toBeGreaterThan(0);
  });

  it("registers a company with the complete production form contract", async () => {
    const unique = Date.now();
    const payload: RegisterCompanyInput = {
      legalName: `Automated Registration ${unique}`,
      tradingName: `Automated Registration ${unique}`,
      country: "India",
      industry: "Manufacturing",
      registrationNumber: `REG-${unique}`,
      taxId: `TAX-${unique}`,
      primaryContactName: "Backend Test Contact",
      primaryContactEmail: `contact-${unique}@test.invalid`,
      phoneNumber: "+91 9000000000",
      website: "https://company.test.invalid",
      defaultCurrency: "INR",
      defaultLanguage: "English",
      timezone: "Asia/Kolkata",
      preferredAccountingSystem: "SAP S/4HANA",
    };
    const result = await companyApi.register(payload);
    expect(result.status).toBe("registered");
    expect(result.payload.primaryContactEmail).toBe(payload.primaryContactEmail);
  });

  it("validates and creates a shared-link ingestion source", async () => {
    const payload: SharedLinkInput = {
      clientName: process.env.BACKEND_TEST_COMPANY_NAME ?? "Backend Test Company",
      sourceType: "SharePoint",
      provider: "SharePoint",
      name: "Backend Test Source",
      url: process.env.BACKEND_TEST_SHARED_LINK_URL ?? "https://sharepoint.test.invalid/sites/finance",
      authenticationType: "OAuth",
      folderPath: "/Invoices",
      fileFilters: "*.pdf, *.xlsx, *.jpg",
      schedule: "Manual",
      defaultCompanyCode: process.env.BACKEND_TEST_COMPANY_CODE ?? "TEST",
      defaultCurrency: "INR",
      defaultReviewerGroup: "Finance Reviewers",
      defaultAccountingIntegration: "SAP S/4HANA",
      allowedDomain: process.env.BACKEND_TEST_ALLOWED_DOMAIN ?? "sharepoint.test.invalid",
    };
    const source = await ingestionApi.createSharedLink(payload);
    expect(source.id).toEqual(expect.any(String));
    expect(source.defaultCompanyCode).toBe(payload.defaultCompanyCode);
  });

  it("returns batch-table records with operational progress fields", async () => {
    const batches = await batchApi.getBatches();
    expect(Array.isArray(batches)).toBe(true);
    for (const batch of batches) {
      expect(batch).toMatchObject({ id: expect.any(String), totalFiles: expect.any(Number), processedFiles: expect.any(Number) });
    }
  });

  it("saves an entry review and completes an approval action when a candidate exists", async () => {
    const tasks = await reviewApi.getTasks();
    const candidate = tasks.find((task) => !task.entry.issues.some((issue) => issue.severity === "error"));
    if (!candidate) return;

    let task = await reviewApi.saveReview(candidate.id, {
      accountingEntry: candidate.entry.accountingEntry,
      checklist: candidate.checklist.map((item) => ({ ...item, checked: true })),
      reviewerComments: "Reviewed by the backend integration test.",
    }, actor);

    if (task.secondApprovalRequired) task = await reviewApi.sendForSecondApproval(task.id, actor, "Escalated for required second approval.");
    const result = await reviewApi.approve(task.id, actor, "Approved by the backend integration test.");
    expect(result.failed).toEqual([]);
    expect(result.succeeded).toContain(task.id);
  });

  it("executes an SAP posting when a posting record exists", async () => {
    const records = await sapApi.getPostingRecords();
    if (!records[0]) return;

    const posting = await sapApi.executePosting(records[0].id);
    expect(posting.sapStatus).toBe("posted");
    expect(posting.sapDocumentNumber).toEqual(expect.any(String));
    expect(posting.response?.success).toBe(true);
  });

  it("supports the Super Admin company table contract", async () => {
    const companies = await superAdminApi.getCompanies();
    expect(Array.isArray(companies)).toBe(true);
    for (const company of companies) {
      expect(company).toMatchObject({
        companyName: expect.any(String),
        tenantId: expect.any(String),
        adminEmail: expect.stringContaining("@"),
        status: expect.any(String),
      });
    }
  });

  it("routes single-role and multi-role users to the correct role dashboard", () => {
    expect(getDashboardRole(["reviewer"])).toBe("reviewer");
    expect(getDashboardRole(["company_owner", "approver"], "approver")).toBe("approver");
    expect(dashboardRolePaths.sap_poster).toBe("sap-poster");
    expect(dashboardRolePaths.read_only).toBe("read-only");
  });

  it("reaches the configured backend health endpoint", async () => {
    await expect(apiRequest<{ status: string }>("/health")).resolves.toMatchObject({ status: expect.any(String) });
  });
}, 20_000);
