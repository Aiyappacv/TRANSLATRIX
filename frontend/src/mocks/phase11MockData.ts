import type { RoleCode, RoleDashboardDefinition } from "@/types";

const roles: Exclude<RoleCode, "spectra_super_admin">[] = [
  "company_owner",
  "company_admin",
  "finance_manager",
  "finance_user",
  "reviewer",
  "approver",
  "sap_poster",
  "integration_manager",
  "auditor",
  "read_only",
];

const emptyDashboard = (role: Exclude<RoleCode, "spectra_super_admin">): RoleDashboardDefinition => ({
  role,
  title: "Dashboard",
  subtitle: "Operational data is supplied by the backend.",
  focus: "Backend-connected workspace",
  readOnly: role === "read_only" || role === "auditor",
  kpis: [],
  tasks: [],
  processing: [],
  sapPosting: [],
  validation: [],
  integrations: [],
  categoryBreakdown: [],
  recentFiles: [],
  recentEntries: [],
  auditActivity: [],
  quickActions: [],
});

export const roleDashboardDefinitions = Object.fromEntries(roles.map((role) => [role, emptyDashboard(role)])) as Record<Exclude<RoleCode, "spectra_super_admin">, RoleDashboardDefinition>;
export const dashboardRoleOrder = roles;
