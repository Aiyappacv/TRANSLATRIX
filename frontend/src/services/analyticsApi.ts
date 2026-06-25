import type { DashboardSummary } from "@/types";
import { apiRequest } from "./apiClient";

export const analyticsApi = {
  getSummary: () => apiRequest<DashboardSummary>("/analytics/summary"),
};
