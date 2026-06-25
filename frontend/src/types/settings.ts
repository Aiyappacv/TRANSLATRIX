import type { RoleCode } from "./auth";

export interface CompanySettingsForm {
  legalName: string;
  tradingName: string;
  country: string;
  industry: string;
  registrationNumber: string;
  taxId: string;
  defaultCurrency: string;
  defaultLanguage: string;
  timezone: string;
  defaultCompanyCode: string;
  fiscalYearVariant: string;
  financeContact: string;
  website: string;
  phone: string;
}

export interface ApprovalRulesSettings {
  approvalRequiredAbove: number;
  secondApprovalAbove: number;
  lowConfidenceRequiresReview: boolean;
  confidenceThreshold: number;
  sapFailedRequiresAdminReview: boolean;
  categoryBasedApproval: boolean;
  categoryRules: Array<{ id: string; category: string; approverRole: RoleCode; threshold: number; active: boolean }>;
}

export interface GlAccountMapping {
  id: string;
  category: string;
  subcategory: string;
  keywords: string[];
  glAccount: string;
  costCenterDefault?: string;
  taxCodeDefault?: string;
  priority: number;
  active: boolean;
}

export interface OcrSettings {
  primaryEngine: "Mistral OCR" | "PaddleOCR" | "Azure Document Intelligence" | "AWS Textract" | "Google Document AI";
  fallbackEngine: "Azure Document Intelligence" | "AWS Textract" | "Google Document AI";
  cloudFallbackEnabled: boolean;
  confidenceThreshold: number;
  tableExtractionEnabled: boolean;
  layoutAnalysisEnabled: boolean;
  handwritingEnabled: boolean;
  maxPagesPerFile: number;
}

export interface SecuritySettings {
  mfaRequired: boolean;
  mfaRequiredForPrivilegedRoles: boolean;
  passwordMinimumLength: number;
  passwordRequireUppercase: boolean;
  passwordRequireLowercase: boolean;
  passwordRequireNumber: boolean;
  passwordRequireSymbol: boolean;
  passwordExpiryDays: number;
  sessionTimeoutMinutes: number;
  allowedIpRanges: string;
  ssoEnabled: boolean;
  ssoProvider: string;
  auditRetentionDays: number;
}

export interface PermissionMatrixRow {
  feature: string;
  permissions: Partial<Record<RoleCode, "none" | "read" | "manage">>;
}
