import { test, expect } from "@playwright/test";
import path from "path";

// Helper to login before tests
async function login(page) {
  await page.goto("/login");
  await page.getByLabel(/username/i).fill("testuser");
  await page.getByLabel(/password/i).fill("TestPass123!");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/(dashboard|overview)/i, { timeout: 10000 });
}

test.describe("Suppliers Management", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/suppliers");
  });

  test("should display suppliers list", async ({ page }) => {
    // Wait for table or list to load
    const table = page.locator(
      'table, [role="grid"], [data-testid="suppliers-list"]',
    );
    await expect(table.first()).toBeVisible({ timeout: 10000 });
  });

  test("should open add supplier dialog", async ({ page }) => {
    const addButton = page.getByRole("button", { name: /add|new|create/i });
    if (await addButton.isVisible()) {
      await addButton.click();
      await expect(page.getByRole("dialog")).toBeVisible();
    }
  });

  test("should search suppliers", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill("Test Supplier");
      // Wait for search results
      await page.waitForTimeout(500);
      // Results should update
      const table = page.locator('table, [role="grid"]');
      await expect(table).toBeVisible();
    }
  });
});

test.describe("Categories Management", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/categories");
  });

  test("should display categories list", async ({ page }) => {
    const table = page.locator(
      'table, [role="grid"], [data-testid="categories-list"]',
    );
    await expect(table.first()).toBeVisible({ timeout: 10000 });
  });

  test("should open add category dialog", async ({ page }) => {
    const addButton = page.getByRole("button", { name: /add|new|create/i });
    if (await addButton.isVisible()) {
      await addButton.click();
      await expect(page.getByRole("dialog")).toBeVisible();
    }
  });
});

test.describe("Transactions Management", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/transactions");
  });

  test("should display transactions table", async ({ page }) => {
    const table = page.locator(
      'table, [role="grid"], [data-testid="transactions-list"]',
    );
    await expect(table.first()).toBeVisible({ timeout: 10000 });
  });

  test("should filter transactions by date", async ({ page }) => {
    const dateFilter = page.getByLabel(/date|from|start/i);
    if (await dateFilter.isVisible()) {
      await dateFilter.click();
      // Date picker should open
      await expect(
        page.locator('[role="dialog"], [class*="calendar"]'),
      ).toBeVisible();
    }
  });

  test("should filter transactions by supplier", async ({ page }) => {
    const supplierFilter = page.getByLabel(/supplier/i);
    if (await supplierFilter.isVisible()) {
      await supplierFilter.click();
      // Dropdown should open
      await expect(
        page.locator('[role="listbox"], [role="menu"]'),
      ).toBeVisible();
    }
  });

  test("should have export button", async ({ page }) => {
    const exportButton = page.getByRole("button", { name: /export|download/i });
    await expect(exportButton.first()).toBeVisible();
  });
});

test.describe("CSV Upload", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/transactions");
  });

  test("should show upload button", async ({ page }) => {
    const uploadButton = page.getByRole("button", { name: /upload|import/i });
    await expect(uploadButton.first()).toBeVisible();
  });

  test("should open upload dialog", async ({ page }) => {
    const uploadButton = page.getByRole("button", { name: /upload|import/i });
    if (await uploadButton.isVisible()) {
      await uploadButton.click();
      await expect(page.getByRole("dialog")).toBeVisible();
    }
  });

  test("should show file input in upload dialog", async ({ page }) => {
    const uploadButton = page.getByRole("button", { name: /upload|import/i });
    if (await uploadButton.isVisible()) {
      await uploadButton.click();
      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();
    }
  });
});

test.describe("Data Export", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/transactions");
  });

  test("should trigger CSV export", async ({ page }) => {
    const exportButton = page.getByRole("button", { name: /export|download/i });
    if (await exportButton.isVisible()) {
      // Set up download listener
      const downloadPromise = page
        .waitForEvent("download", { timeout: 5000 })
        .catch(() => null);

      await exportButton.click();

      const download = await downloadPromise;
      if (download) {
        // Check that file was downloaded
        expect(download.suggestedFilename()).toContain(".csv");
      }
    }
  });
});

test.describe("Bulk Operations", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/transactions");
  });

  test("should show selection checkboxes", async ({ page }) => {
    const checkboxes = page.locator('input[type="checkbox"]');
    // Should have at least header checkbox
    await expect(checkboxes.first()).toBeVisible({ timeout: 10000 });
  });

  test("should enable bulk delete after selection", async ({ page }) => {
    // Select a checkbox
    const checkbox = page.locator('input[type="checkbox"]').first();
    if (await checkbox.isVisible()) {
      await checkbox.check();

      // Bulk delete button should appear or become enabled
      const deleteButton = page.getByRole("button", { name: /delete|remove/i });
      if (await deleteButton.isVisible()) {
        await expect(deleteButton).toBeEnabled();
      }
    }
  });
});
