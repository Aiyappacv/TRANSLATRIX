import type { RoleCode } from "@/types";

export const dashboardRolePaths: Partial<Record<RoleCode, string>> = {
  company_owner: "owner",
  company_admin: "admin",
  finance_manager: "finance-manager",
  finance_user: "finance-user",
  reviewer: "reviewer",
  approver: "approver",
  sap_poster: "sap-poster",
  integration_manager: "integration-manager",
  auditor: "auditor",
  read_only: "read-only",
};

export const dashboardPathRoles = Object.fromEntries(
  Object.entries(dashboardRolePaths).map(([role, path]) => [path, role]),
) as Record<string, RoleCode>;

export function getDashboardRole(roles: RoleCode[], activeRole?: RoleCode | null): RoleCode {
  if (activeRole && roles.includes(activeRole) && activeRole !== "spectra_super_admin") return activeRole;
  return roles.find((role) => role !== "spectra_super_admin") ?? "read_only";
}
