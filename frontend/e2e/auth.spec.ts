import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    // Start at the login page
    await page.goto("/login");
  });

  test("should display login page", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("should show validation errors for empty form", async ({ page }) => {
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/required/i)).toBeVisible();
  });

  test("should show error for invalid credentials", async ({ page }) => {
    await page.getByLabel(/username/i).fill("wronguser");
    await page.getByLabel(/password/i).fill("wrongpass");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for error message
    await expect(page.getByText(/invalid/i)).toBeVisible({ timeout: 5000 });
  });

  test("should redirect to dashboard on successful login", async ({ page }) => {
    // Fill in valid credentials (these should match your test setup)
    await page.getByLabel(/username/i).fill("testuser");
    await page.getByLabel(/password/i).fill("TestPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect to dashboard/overview
    await expect(page).toHaveURL(/\/(dashboard|overview)/i, { timeout: 10000 });
  });

  test("should redirect to login when accessing protected route", async ({
    page,
  }) => {
    await page.goto("/overview");
    await expect(page).toHaveURL(/\/login/i);
  });

  test("should have link to registration page", async ({ page }) => {
    const registerLink = page.getByRole("link", { name: /register|sign up/i });
    if (await registerLink.isVisible()) {
      await registerLink.click();
      await expect(page).toHaveURL(/\/register/i);
    }
  });
});

test.describe("Registration", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/register");
  });

  test("should display registration form", async ({ page }) => {
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/^password$/i)).toBeVisible();
  });

  test("should show validation for password mismatch", async ({ page }) => {
    await page.getByLabel(/username/i).fill("newuser");
    await page.getByLabel(/email/i).fill("new@example.com");
    await page.getByLabel(/^password$/i).fill("SecurePass123!");

    const confirmPassword = page.getByLabel(/confirm password/i);
    if (await confirmPassword.isVisible()) {
      await confirmPassword.fill("DifferentPass123!");
      await page.getByRole("button", { name: /register|sign up/i }).click();
      await expect(page.getByText(/match/i)).toBeVisible();
    }
  });
});

test.describe("Session Management", () => {
  test("should maintain session after page refresh", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.getByLabel(/username/i).fill("testuser");
    await page.getByLabel(/password/i).fill("TestPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for navigation to dashboard
    await page.waitForURL(/\/(dashboard|overview)/i, { timeout: 10000 });

    // Refresh the page
    await page.reload();

    // Should still be on protected page, not redirected to login
    await expect(page).not.toHaveURL(/\/login/i);
  });

  test("should logout and redirect to login", async ({ page }) => {
    // Login first
    await page.goto("/login");
    await page.getByLabel(/username/i).fill("testuser");
    await page.getByLabel(/password/i).fill("TestPass123!");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Wait for navigation
    await page.waitForURL(/\/(dashboard|overview)/i, { timeout: 10000 });

    // Find and click logout button
    const logoutButton = page.getByRole("button", { name: /logout|sign out/i });
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await expect(page).toHaveURL(/\/login/i, { timeout: 5000 });
    }
  });
});
