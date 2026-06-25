import type { LoginInput } from "@/schemas/auth.schema";
import type {
  AccountingEntryPayload,
  AuditEvent,
  AuthSession,
  Company,
  CompanyUser,
  DashboardSummary,
  FinancialEntry,
  IngestedFile,
  IngestionBatch,
  IntegrationProvider,
  LinkValidationResult,
  OnboardingState,
  PostingResult,
  SapMappingRule,
  SharedLinkSource,
} from "@/types";

const unavailable = async <T,>(): Promise<T> => {
  throw new Error("Local fixture data is not configured. Connect the backend API.");
};

export const mockApi = {
  login: (_input: LoginInput): Promise<AuthSession> => unavailable<AuthSession>(),
  registerCompany: async <T,>(payload: T): Promise<{ id: string; status: string; payload: T }> => ({ id: "", status: "registered", payload }),
  getCompanies: async (): Promise<Company[]> => [],
  getCompany: (_companyId?: string): Promise<Company> => unavailable<Company>(),
  getUsers: async (_companyId?: string): Promise<CompanyUser[]> => [],
  getOnboarding: async (): Promise<OnboardingState> => ({ currentStep: "", completion: 0, steps: [] }),
  getSharedLinks: async (): Promise<SharedLinkSource[]> => [],
  getSharedLink: (_id: string): Promise<SharedLinkSource> => unavailable<SharedLinkSource>(),
  getBatches: async (): Promise<IngestionBatch[]> => [],
  getBatch: (_id: string): Promise<IngestionBatch> => unavailable<IngestionBatch>(),
  getFiles: async (): Promise<IngestedFile[]> => [],
  getFile: (_id: string): Promise<IngestedFile> => unavailable<IngestedFile>(),
  getEntries: async (): Promise<FinancialEntry[]> => [],
  getValidationIssues: async (): Promise<FinancialEntry[]> => [],
  getEntry: (_id: string): Promise<FinancialEntry> => unavailable<FinancialEntry>(),
  getSapPayload: (): Promise<AccountingEntryPayload> => unavailable<AccountingEntryPayload>(),
  getMappings: async (): Promise<SapMappingRule[]> => [],
  getPostingResults: async (): Promise<PostingResult[]> => [],
  getIntegrations: async (): Promise<IntegrationProvider[]> => [],
  getAuditEvents: async (): Promise<AuditEvent[]> => [],
  getDashboardSummary: async (): Promise<DashboardSummary> => ({ kpis: [], processingTrend: [], classificationSplit: [] }),
  approveReviewTask: async (id: string): Promise<{ id: string; status: "approved" }> => ({ id, status: "approved" }),
  rejectReviewTask: async (id: string, reason: string): Promise<{ id: string; status: "rejected"; reason: string }> => ({ id, status: "rejected", reason }),
  testIntegration: async (providerCode: string): Promise<{ providerCode: string; status: "success"; latencyMs: number; checkedAt: string }> => ({ providerCode, status: "success", latencyMs: 0, checkedAt: new Date().toISOString() }),
  validateSharedLink: (_payload: unknown): Promise<LinkValidationResult> => unavailable<LinkValidationResult>(),
};
