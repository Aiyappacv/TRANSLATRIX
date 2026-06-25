import { expect, test, type Page } from "@playwright/test";

const sharedPassword = process.env.E2E_USER_PASSWORD;

async function signIn(page: Page, email: string, password: string) {
  await page.goto("/auth/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(page).not.toHaveURL(/\/auth\/login$/);
}

test("login starts with empty credentials and no demo account controls", async ({ page }) => {
  await page.goto("/auth/login");

  await expect(page.getByLabel("Work email")).toHaveValue("");
  await expect(page.getByLabel("Password")).toHaveValue("");
  await expect(page.getByTestId("selected-login-role")).toHaveCount(0);
  await expect(page.getByText(/demo account|common password/i)).toHaveCount(0);
});

test("integration manager can register a custom connector", async ({ page }) => {
  const email = process.env.E2E_INTEGRATION_MANAGER_EMAIL;
  test.skip(!email || !sharedPassword, "Set E2E_INTEGRATION_MANAGER_EMAIL and E2E_USER_PASSWORD for this backend-connected test.");

  await signIn(page, email!, sharedPassword!);
  await page.goto("/app/integrations");
  await page.getByRole("button", { name: "Register custom connector" }).click();

  const unique = Date.now();
  const code = `e2e_connector_${unique}`;
  await page.getByLabel("Connector name").fill("Automated Ledger Gateway");
  await page.getByLabel("Unique code").fill(code);
  await page.getByLabel("Base URL").fill("https://connector.test.invalid/api");
  await page.getByLabel("Description").fill("Automated accounting connector interaction test.");
  await page.getByRole("button", { name: "Register connector" }).click();

  await expect(page).toHaveURL(new RegExp(`/app/integrations/${code}$`));
  await expect(page.getByText("Automated Ledger Gateway").first()).toBeVisible();
});

test("super admin can provision and suspend a tenant", async ({ page }) => {
  const email = process.env.E2E_SUPER_ADMIN_EMAIL;
  test.skip(!email || !sharedPassword, "Set E2E_SUPER_ADMIN_EMAIL and E2E_USER_PASSWORD for this backend-connected test.");

  await signIn(page, email!, sharedPassword!);
  await page.goto("/super-admin/company-onboarding");

  const unique = Date.now();
  const companyName = `Automated Tenant ${unique}`;
  await page.getByLabel("Legal company name").fill(companyName);
  await page.getByLabel("Company admin email").fill(`admin-${unique}@test.invalid`);
  await page.getByLabel("Country").fill("India");
  await page.getByLabel("Industry").fill("Professional Services");
  await page.getByLabel("Default company code").fill(`T${String(unique).slice(-3)}`);
  await page.getByRole("button", { name: "Start provisioning" }).click();

  await expect(page).toHaveURL(/\/super-admin\/companies\/company_/);
  await expect(page.getByRole("heading", { name: companyName })).toBeVisible();
  await page.getByRole("button", { name: "Suspend tenant" }).click();
  await page.getByRole("button", { name: "Suspend tenant" }).last().click();
  await expect(page.getByRole("button", { name: "Reactivate tenant" })).toBeVisible();
});

test("company admin can invite and activate a company user", async ({ page }) => {
  const email = process.env.E2E_COMPANY_ADMIN_EMAIL;
  test.skip(!email || !sharedPassword, "Set E2E_COMPANY_ADMIN_EMAIL and E2E_USER_PASSWORD for this backend-connected test.");

  await signIn(page, email!, sharedPassword!);
  await page.goto("/app/settings/users-roles");
  await page.getByRole("button", { name: "Invite user" }).click();

  const unique = Date.now();
  const invitedEmail = `automated-user-${unique}@test.invalid`;
  await page.getByLabel("Name").fill("Automated Finance User");
  await page.getByLabel("Email").fill(invitedEmail);
  await page.getByRole("button", { name: "Create invitation" }).click();

  await expect(page.getByText(invitedEmail)).toBeVisible();
  const row = page.getByRole("row", { name: new RegExp(invitedEmail) });
  await row.getByRole("button", { name: "Activate" }).click();
  await expect(row.getByText("active")).toBeVisible();
});
