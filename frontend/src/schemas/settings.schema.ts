import { z } from "zod";

export const companySettingsSchema = z.object({
  legalName: z.string().min(2, "Legal name is required"),
  tradingName: z.string().trim().optional().default(""),
  country: z.string().min(2),
  industry: z.string().trim().optional().default(""),
  registrationNumber: z.string().trim().optional().default(""),
  taxId: z.string().trim().optional().default(""),
  defaultCurrency: z.string().length(3),
  defaultLanguage: z.string().min(2),
  timezone: z.string().min(3),
  defaultCompanyCode: z.string().min(2).max(8),
  fiscalYearVariant: z.string().min(2),
  financeContact: z.string().email(),
  website: z.union([z.literal(""), z.string().url("Enter a valid website URL")]),
  phone: z.union([z.literal(""), z.string().min(8, "Enter a valid phone number")]),
});

export const approvalRulesSchema = z.object({
  approvalRequiredAbove: z.coerce.number().min(0),
  secondApprovalAbove: z.coerce.number().min(0),
  lowConfidenceRequiresReview: z.boolean(),
  confidenceThreshold: z.coerce.number().min(0).max(100),
  sapFailedRequiresAdminReview: z.boolean(),
  categoryBasedApproval: z.boolean(),
  categoryRules: z.array(z.object({
    id: z.string(),
    category: z.string(),
    approverRole: z.enum(["company_owner", "company_admin", "finance_manager", "finance_user", "reviewer", "approver", "sap_poster", "integration_manager", "auditor", "read_only", "spectra_super_admin"]),
    threshold: z.coerce.number().min(0),
    active: z.boolean(),
  })),
}).refine((value) => value.secondApprovalAbove >= value.approvalRequiredAbove, { message: "Second approval threshold must be greater than or equal to the first approval threshold.", path: ["secondApprovalAbove"] });

export const ocrSettingsSchema = z.object({
  primaryEngine: z.enum(["Mistral OCR", "PaddleOCR", "Azure Document Intelligence", "AWS Textract", "Google Document AI"]),
  fallbackEngine: z.enum(["Azure Document Intelligence", "AWS Textract", "Google Document AI"]),
  cloudFallbackEnabled: z.boolean(),
  confidenceThreshold: z.coerce.number().min(0).max(100),
  tableExtractionEnabled: z.boolean(),
  layoutAnalysisEnabled: z.boolean(),
  handwritingEnabled: z.boolean(),
  maxPagesPerFile: z.coerce.number().int().min(1).max(5000),
});

export const securitySettingsSchema = z.object({
  mfaRequired: z.boolean(),
  mfaRequiredForPrivilegedRoles: z.boolean(),
  passwordMinimumLength: z.coerce.number().int().min(8).max(64),
  passwordRequireUppercase: z.boolean(),
  passwordRequireLowercase: z.boolean(),
  passwordRequireNumber: z.boolean(),
  passwordRequireSymbol: z.boolean(),
  passwordExpiryDays: z.coerce.number().int().min(0).max(365),
  sessionTimeoutMinutes: z.coerce.number().int().min(5).max(1440),
  allowedIpRanges: z.string(),
  ssoEnabled: z.boolean(),
  ssoProvider: z.string(),
  auditRetentionDays: z.coerce.number().int().min(30).max(3650),
}).superRefine((value, context) => {
  if (value.ssoEnabled && value.ssoProvider.trim().length < 2) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["ssoProvider"], message: "SSO provider is required when SSO is enabled" });
  }
});
