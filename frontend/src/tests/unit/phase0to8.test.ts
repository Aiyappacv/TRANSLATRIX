import { describe, expect, it } from "vitest";
import { sharedLinkSchema } from "@/schemas/ingestion.schema";
import { onboardingDraftSchema, onboardingIntegrations, onboardingRoles } from "@/schemas/onboarding.schema";
import { entryApi } from "@/services/entryApi";
import type { FinancialEntry } from "@/types";

const sharedLinkBase = {
  clientName: "Aruna Textile",
  sourceType: "Google Drive" as const,
  provider: "Google Drive" as const,
  name: "Monthly invoices",
  url: "https://drive.example.com/invoices",
  authenticationType: "OAuth" as const,
  folderPath: "/Finance/Invoices",
  fileFilters: "*.pdf,*.xlsx",
  schedule: "Daily" as const,
  defaultCompanyCode: "AT01",
  defaultCurrency: "INR",
  defaultReviewerGroup: "Finance Reviewers",
  defaultAccountingIntegration: "SAP S/4HANA",
};

const accountingEntry: FinancialEntry["accountingEntry"] = {
  header: {
    documentType: "KR",
    companyCode: "AT01",
    postingDate: "2026-06-13",
    documentDate: "2026-06-13",
    reference: "INV-1001",
    headerText: "Vendor invoice",
  },
  debitLines: [{
    id: "debit-1",
    type: "debit",
    glAccount: "510000",
    accountName: "Office expenses",
    costCenter: "FIN",
    taxCode: "V1",
    amount: 100,
    currency: "INR",
    memo: "Expense",
  }],
  creditLines: [{
    id: "credit-1",
    type: "credit",
    glAccount: "200000",
    accountName: "Vendor payable",
    amount: 100,
    currency: "INR",
    memo: "Payable",
  }],
};

describe("phase 0-8 production rules", () => {
  it("requires an endpoint for connected shared-link sources", () => {
    const result = sharedLinkSchema.safeParse({ ...sharedLinkBase, url: "" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((issue) => issue.path[0] === "url")).toBe(true);
    }
  });

  it("allows local upload without a remote URL", () => {
    const result = sharedLinkSchema.safeParse({
      ...sharedLinkBase,
      sourceType: "Local Upload",
      provider: "Local Upload",
      authenticationType: "None",
      url: "",
    });
    expect(result.success).toBe(true);
  });

  it("validates the complete six-step onboarding payload", () => {
    const payload = {
      companyProfile: {
        legalName: "Aruna Textile Private Limited",
        tradingName: "Aruna Textile",
        country: "India",
        industry: "Textiles",
        registrationNumber: "CIN-AT-1001",
        taxId: "GSTIN29ABCDE1234F1Z5",
        primaryContactName: "Company Administrator",
        primaryContactEmail: "admin@arunatextile.com",
        phoneNumber: "+91 9000000000",
        website: "https://arunatextile.example",
        defaultCurrency: "INR",
        defaultLanguage: "English",
        timezone: "Asia/Kolkata",
      },
      finance: {
        companyCode: "AT01",
        fiscalYearVariant: "K4",
        baseCurrency: "INR",
        taxCountry: "IN",
        approvalPolicy: "Dual approval above INR 100000",
      },
      invitations: onboardingRoles.map((role) => ({ role, email: "" })),
      integrations: [onboardingIntegrations[0]],
      security: {
        mfaRequired: true,
        ssoEnabled: false,
        ipRestrictions: "",
      },
    };
    expect(onboardingDraftSchema.safeParse(payload).success).toBe(true);
  });

  it("accepts a balanced, fully mapped accounting entry", async () => {
    const result = await entryApi.validateEntry("ENT-1001", {
      category: "Expenses",
      subcategory: "Office Expenses",
      amount: 100,
      currency: "INR",
      sapTCode: "FB60",
      glAccount: "510000",
      accountingEntry,
    });
    expect(result.validationStatus).toBe("valid");
    expect(result.issues).toHaveLength(0);
  });

  it("rejects an unbalanced accounting entry", async () => {
    const result = await entryApi.validateEntry("ENT-1002", {
      category: "Expenses",
      subcategory: "Office Expenses",
      amount: 100,
      currency: "INR",
      sapTCode: "FB60",
      glAccount: "510000",
      accountingEntry: {
        ...accountingEntry,
        creditLines: accountingEntry.creditLines.map((line) => ({ ...line, amount: 90 })),
      },
    });
    expect(result.validationStatus).toBe("failed");
    expect(result.issues.some((issue) => issue.code === "ACCOUNTING_UNBALANCED")).toBe(true);
  });
});
