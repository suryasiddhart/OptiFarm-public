import { test, expect } from "@playwright/test";

/**
 * FarmApp E2E — Login Flow
 *
 * Tests the basic login page rendering and form interaction.
 * Full authentication flow requires a running backend.
 */

test.describe("Login Page", () => {
  test("should display the login form", async ({ page }) => {
    await page.goto("/login");

    // Verify the page loads with expected elements
    await expect(page.locator("h1, h2, h3").first()).toBeVisible();
    await expect(page.locator('input[type="text"], input[name="username"]').first()).toBeVisible();
    await expect(page.locator('input[type="password"]').first()).toBeVisible();
    await expect(page.locator('button[type="submit"]').first()).toBeVisible();
  });

  test("should show validation errors on empty submit", async ({ page }) => {
    await page.goto("/login");
    await page.locator('button[type="submit"]').first().click();

    // Expect some validation feedback
    await expect(page.locator(".ant-form-item-explain-error").first()).toBeVisible();
  });
});
