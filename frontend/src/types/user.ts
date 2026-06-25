import type { RoleCode } from "./auth";

export interface CompanyUser {
  id: string;
  companyId: string;
  companyName: string;
  name: string;
  email: string;
  role: RoleCode;
  department: string;
  approvalLimit: number;
  status: "invited" | "active" | "disabled";
}

export interface InviteCompanyUserInput {
  companyId: string;
  companyName: string;
  name: string;
  email: string;
  role: RoleCode;
  department?: string;
  approvalLimit?: number;
}
