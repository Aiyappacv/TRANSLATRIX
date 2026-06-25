import type { Company, CompanyUser, InviteCompanyUserInput, RoleCode } from "@/types";
import type { RegisterCompanyInput } from "@/schemas/company.schema";
import { apiRequest } from "./apiClient";

export const companyApi = {
  register: (payload: RegisterCompanyInput) => apiRequest<{ id: string; status: string; payload: RegisterCompanyInput }>("/register", { method: "POST", body: JSON.stringify(payload) }),
  getCompanies: () => apiRequest<Company[]>("/companies"),
  getCompany: (_companyId?: string) => apiRequest<Company>("/companies/current"),
  getUsers: (_companyId?: string) => apiRequest<CompanyUser[]>("/users"),
  inviteUser: (input: InviteCompanyUserInput) => apiRequest<CompanyUser>("/users/invitations", { method: "POST", body: JSON.stringify(input) }),
  updateUserRole: (userId: string, role: RoleCode) => apiRequest<CompanyUser>(`/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ role }) }),
  updateUserStatus: (userId: string, status: CompanyUser["status"]) => apiRequest<CompanyUser>(`/users/${userId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
};
