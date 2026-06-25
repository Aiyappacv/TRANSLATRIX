import { z } from "zod";

export const onboardingRoles = [
  "Company Admin",
  "Finance Manager",
  "Finance User",
  "Reviewer",
  "Approver",
  "SAP Poster",
  "Integration Manager",
  "Auditor",
] as const;

export const onboardingIntegrations = [
  "SAP S/4HANA",
  "QuickBooks",
  "Xero",
  "Zoho Books",
  "TallyPrime",
  "Sage",
  "NetSuite",
  "Manual JSON export",
] as const;

const optionalUrl = z.string().trim().refine((value) => !value || /^https?:\/\//i.test(value), "Use a valid http(s) website URL");

export const onboardingDraftSchema = z.object({
  companyProfile: z.object({
    legalName: z.string().min(2, "Company legal name is required"),
    tradingName: z.string().min(2, "Trading name is required"),
    country: z.string().min(2, "Country is required"),
    industry: z.string().min(2, "Industry is required"),
    registrationNumber: z.string().min(2, "Registration number is required"),
    taxId: z.string().min(3, "Tax/VAT/GST number is required"),
    primaryContactName: z.string().min(2, "Primary contact name is required"),
    primaryContactEmail: z.string().email("Use a valid contact email"),
    phoneNumber: z.string().min(6, "Phone number is required"),
    website: optionalUrl,
    defaultCurrency: z.string().length(3, "Use a 3-letter currency code"),
    defaultLanguage: z.string().min(2),
    timezone: z.string().min(2),
  }),
  finance: z.object({
    companyCode: z.string().min(2, "Company code is required"),
    fiscalYearVariant: z.string().min(2, "Fiscal year variant is required"),
    baseCurrency: z.string().length(3, "Use a 3-letter currency code"),
    taxCountry: z.string().min(2, "Tax country is required"),
    approvalPolicy: z.string().min(5, "Approval policy is required"),
  }),
  invitations: z.array(z.object({
    role: z.enum(onboardingRoles),
    email: z.union([z.literal(""), z.string().email("Use a valid invitation email")]),
  })).length(onboardingRoles.length),
  integrations: z.array(z.enum(onboardingIntegrations)).min(1, "Select at least one integration"),
  security: z.object({
    mfaRequired: z.boolean(),
    ssoEnabled: z.boolean(),
    ipRestrictions: z.string(),
  }),
});

export type OnboardingDraftInput = z.infer<typeof onboardingDraftSchema>;
