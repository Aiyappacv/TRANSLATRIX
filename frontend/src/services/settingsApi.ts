import type {
  ApprovalRulesSettings,
  CompanySettingsForm,
  GlAccountMapping,
  OcrSettings,
  SapMappingRule,
  SecuritySettings,
} from "@/types";
import { apiRequest } from "./apiClient";

export const settingsApi = {
  getMappings: () => apiRequest<SapMappingRule[]>("/settings/mapping-rules"),
  saveMappings: (value: SapMappingRule[]) => apiRequest<SapMappingRule[]>("/settings/sap-tcode-mappings", { method: "PUT", body: JSON.stringify(value) }),
  getGlMappings: () => apiRequest<GlAccountMapping[]>("/settings/gl-account-mappings"),
  saveGlMappings: (value: GlAccountMapping[]) => apiRequest<GlAccountMapping[]>("/settings/gl-account-mappings", { method: "PUT", body: JSON.stringify(value) }),
  getCompanySettings: () => apiRequest<CompanySettingsForm>("/settings/company"),
  saveCompanySettings: (value: CompanySettingsForm) => apiRequest<CompanySettingsForm>("/settings/company", { method: "PUT", body: JSON.stringify(value) }),
  getApprovalRules: () => apiRequest<ApprovalRulesSettings>("/settings/approval-rules"),
  saveApprovalRules: (value: ApprovalRulesSettings) => apiRequest<ApprovalRulesSettings>("/settings/approval-rules", { method: "PUT", body: JSON.stringify(value) }),
  getOcrSettings: () => apiRequest<OcrSettings>("/settings/ocr"),
  saveOcrSettings: (value: OcrSettings) => apiRequest<OcrSettings>("/settings/ocr", { method: "PUT", body: JSON.stringify(value) }),
  getSecuritySettings: () => apiRequest<SecuritySettings>("/settings/security"),
  saveSecuritySettings: (value: SecuritySettings) => apiRequest<SecuritySettings>("/settings/security", { method: "PUT", body: JSON.stringify(value) }),
};
