import type { FinancialEntry, ValidationIssue } from "@/types";
import { apiRequest } from "./apiClient";

export const entryApi = {
  getEntries: () => apiRequest<FinancialEntry[]>("/entries"),
  getValidationIssues: () => apiRequest<FinancialEntry[]>("/entries/validation-issues"),
  getEntry: (id: string) => apiRequest<FinancialEntry>(`/entries/${id}`),
  updateEntry: (id: string, patch: Partial<FinancialEntry>) => apiRequest<FinancialEntry>(`/entries/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  validateEntry: (id: string, candidate: Pick<FinancialEntry, "category" | "subcategory" | "amount" | "currency" | "sapTCode" | "glAccount" | "accountingEntry"> & Partial<FinancialEntry>) => apiRequest<{ validationStatus: FinancialEntry["validationStatus"]; issues: ValidationIssue[] }>(`/entries/${id}/validate`, { method: "POST", body: JSON.stringify(candidate) }),
  resubmit: (id: string, comments?: string) => apiRequest<FinancialEntry>(`/entries/${id}/resubmit`, { method: "POST", body: JSON.stringify({ comments }) }),
  markReviewed: (id: string, comments?: string) => apiRequest<FinancialEntry>(`/entries/${id}/mark-reviewed`, { method: "POST", body: JSON.stringify({ comments }) }),
  approveEntry: (id: string, comments?: string) => apiRequest<FinancialEntry>(`/entries/${id}/approve`, { method: "POST", body: JSON.stringify({ comments }) }),
  rejectEntry: (id: string, comments: string) => apiRequest<FinancialEntry>(`/entries/${id}/reject`, { method: "POST", body: JSON.stringify({ comments }) }),
  requestCorrection: (id: string, comments: string) => apiRequest<FinancialEntry>(`/entries/${id}/request-correction`, { method: "POST", body: JSON.stringify({ comments }) }),
};
