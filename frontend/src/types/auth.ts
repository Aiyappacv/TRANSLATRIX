import type { Permission } from "@/utils/permissions";

export type RoleCode =
  | "spectra_super_admin"
  | "company_owner"
  | "company_admin"
  | "finance_manager"
  | "finance_user"
  | "reviewer"
  | "approver"
  | "sap_poster"
  | "integration_manager"
  | "auditor"
  | "read_only";

export interface Role {
  code: RoleCode;
  name: string;
  permissions: Permission[];
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  tenantId: string;
  companyId: string;
  companyName: string;
  roles: RoleCode[];
  permissions: Permission[];
  mfaEnabled: boolean;
  isPlatformOwner?: boolean;
  canSwitchCompanies?: boolean;
}


export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresIn?: number;
  mfaRequired?: false;
  user: User;
}

export interface MfaChallenge {
  mfaRequired: true;
  mfaSetupRequired: boolean;
  challengeToken: string;
  expiresIn: number;
  email: string;
  secret?: string;
  otpauthUri?: string;
}

export type LoginResult = AuthSession | MfaChallenge;

export function isAuthSession(result: LoginResult): result is AuthSession {
  return "accessToken" in result && Boolean(result.accessToken);
}
