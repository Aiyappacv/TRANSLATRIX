export type TenantStatus = "registered" | "email_verified" | "onboarding_started" | "integration_configured" | "sandbox_tested" | "approved" | "active" | "suspended" | "cancelled" | "archived";

export interface Tenant {
  id: string;
  name: string;
  status: TenantStatus;
  region: string;
  plan: "growth" | "enterprise" | "regulated";
}
