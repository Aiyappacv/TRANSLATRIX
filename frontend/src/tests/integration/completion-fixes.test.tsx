import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LoginPage } from "@/pages/auth/LoginPage";
import { accountingIntegrationApi } from "@/services/accountingIntegrationApi";
import { companyApi } from "@/services/companyApi";
import { superAdminApi } from "@/services/superAdminApi";

function renderLogin() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/auth/login"]}>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const backendIt = process.env.RUN_BACKEND_INTEGRATION_TESTS === "true" ? it : it.skip;

describe("Completed phase interactions", () => {
  it("renders an empty production login form without demo account controls", () => {
    renderLogin();

    expect(screen.getByLabelText("Work email")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.queryByTestId("selected-login-role")).not.toBeInTheDocument();
    expect(screen.queryByText(/demo account|common password/i)).not.toBeInTheDocument();
  });

  backendIt("registers and returns a custom accounting connector through the backend", async () => {
    const uniqueCode = `test_connector_${Date.now()}`;
    const created = await accountingIntegrationApi.registerCustomConnector({
      name: "Test Ledger Connector",
      code: uniqueCode,
      type: "accounting",
      description: "Backend connector contract test.",
      baseUrl: "https://connector.test.invalid/api",
      authType: "api_key",
      environment: "sandbox",
    });

    const providers = await accountingIntegrationApi.getProviders();
    expect(created.provider.code).toBe(uniqueCode);
    expect(providers.some((provider) => provider.code === uniqueCode)).toBe(true);
  });

  backendIt("provisions a tenant and supports audited suspend and reactivate actions", async () => {
    const unique = Date.now();
    const result = await superAdminApi.createCompany({
      legalName: `Automated Company ${unique}`,
      adminEmail: `admin-${unique}@test.invalid`,
      country: "India",
      industry: "Professional Services",
      plan: "Growth",
      defaultCurrency: "INR",
      companyCode: `T${String(unique).slice(-3)}`,
      timezone: "Asia/Kolkata",
      requireMfa: true,
      allowAuditedSupportAccess: true,
    });

    expect(result.status).toBe("completed");
    await expect(superAdminApi.setCompanyStatus(result.company.id, "suspended")).resolves.toMatchObject({ status: "suspended" });
    await expect(superAdminApi.setCompanyStatus(result.company.id, "active")).resolves.toMatchObject({ status: "active" });
  });

  backendIt("persists company user invitation, role, and lifecycle changes", async () => {
    const companyId = process.env.BACKEND_TEST_COMPANY_ID;
    const companyName = process.env.BACKEND_TEST_COMPANY_NAME;
    if (!companyId || !companyName) throw new Error("Set BACKEND_TEST_COMPANY_ID and BACKEND_TEST_COMPANY_NAME.");

    const unique = Date.now();
    const invited = await companyApi.inviteUser({
      companyId,
      companyName,
      name: "Automated Test User",
      email: `automated-user-${unique}@test.invalid`,
      role: "finance_user",
      department: "Finance",
      approvalLimit: 50000,
    });

    const promoted = await companyApi.updateUserRole(invited.id, "reviewer");
    const activated = await companyApi.updateUserStatus(invited.id, "active");
    const users = await companyApi.getUsers(companyId);

    expect(promoted.role).toBe("reviewer");
    expect(activated.status).toBe("active");
    expect(users.find((item) => item.id === invited.id)).toMatchObject({ role: "reviewer", status: "active" });
  });
}, 20_000);
