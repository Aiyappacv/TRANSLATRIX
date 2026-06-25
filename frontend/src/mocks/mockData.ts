import type {
  AccountingEntryPayload,
  AuditEvent,
  Company,
  CompanyUser,
  DashboardSummary,
  FinancialEntry,
  IngestedFile,
  IngestionBatch,
  IntegrationProvider,
  OnboardingState,
  PostingResult,
  SapMappingRule,
  SharedLinkSource,
  User,
} from "@/types";

// Production-clean fixture module. No example users, credentials, companies, documents, entries, or postings are bundled.
export const mockCompanies: Company[] = [];
export const mockUsers: User[] = [];
export const mockUser = null as unknown as User;
export const mockCompany = null as unknown as Company;
export const mockCompanyUsers: CompanyUser[] = [];
export const mockOnboarding: OnboardingState = { currentStep: "", completion: 0, steps: [] };
export const mockSharedLinks: SharedLinkSource[] = [];
export const mockBatches: IngestionBatch[] = [];
export const mockFiles: IngestedFile[] = [];
export const mockFile = null as unknown as IngestedFile;
export const mockEntries: FinancialEntry[] = [];
export const mockSapPayload: AccountingEntryPayload = {
  tenant_id: "",
  company_id: "",
  entry_id: "",
  category: "",
  posting_type: "",
  header: { posting_date: "", document_date: "", currency: "", reference: "" },
  parties: {},
  lines: [],
};
export const mockMappings: SapMappingRule[] = [];
export const mockPostingResults: PostingResult[] = [];
export const mockIntegrations: IntegrationProvider[] = [];
export const mockAuditEvents: AuditEvent[] = [];
export const mockDashboardSummary: DashboardSummary = { kpis: [], processingTrend: [], classificationSplit: [] };
