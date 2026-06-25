import type { RoleCode, RoleDashboardDefinition } from "@/types";
import { apiRequest } from "./apiClient";

export const dashboardApi = {
  getRoleDashboard: (role: RoleCode) => apiRequest<RoleDashboardDefinition>(`/dashboards/${role}`),
};
