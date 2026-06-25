import { expect, test } from "@playwright/test";

const testEmail = process.env.E2E_USER_EMAIL;
const testPassword = process.env.E2E_USER_PASSWORD;

test("an authenticated user signs in and reaches an authorized page", async ({ page }) => {
  test.skip(!testEmail || !testPassword, "Set E2E_USER_EMAIL and E2E_USER_PASSWORD for backend-connected authentication tests.");

  await page.goto("/auth/login");
  await page.getByLabel("Work email").fill(testEmail!);
  await page.getByLabel("Password").fill(testPassword!);
  await page.getByRole("button", { name: "Sign in securely" }).click();

  await expect(page).not.toHaveURL(/\/auth\/login$/);
});
