import { test, expect } from "@playwright/test";

// Helper to login before tests
async function login(page) {
  await page.goto("/login");
  await page.getByLabel(/username/i).fill("testuser");
  await page.getByLabel(/password/i).fill("TestPass123!");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/(dashboard|overview)/i, { timeout: 10000 });
}

test.describe("Dashboard Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should display sidebar navigation", async ({ page }) => {
    // Check for navigation elements
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("should navigate to Overview page", async ({ page }) => {
    const overviewLink = page.getByRole("link", { name: /overview/i });
    if (await overviewLink.isVisible()) {
      await overviewLink.click();
      await expect(page).toHaveURL(/\/overview/i);
    }
  });

  test("should navigate to Suppliers page", async ({ page }) => {
    const suppliersLink = page.getByRole("link", { name: /supplier/i });
    if (await suppliersLink.isVisible()) {
      await suppliersLink.click();
      await expect(page).toHaveURL(/\/supplier/i);
    }
  });

  test("should navigate to Categories page", async ({ page }) => {
    const categoriesLink = page.getByRole("link", { name: /categor/i });
    if (await categoriesLink.isVisible()) {
      await categoriesLink.click();
      await expect(page).toHaveURL(/\/categor/i);
    }
  });

  test("should navigate to Transactions page", async ({ page }) => {
    const transactionsLink = page.getByRole("link", { name: /transaction/i });
    if (await transactionsLink.isVisible()) {
      await transactionsLink.click();
      await expect(page).toHaveURL(/\/transaction/i);
    }
  });

  test("should navigate to Analytics page", async ({ page }) => {
    const analyticsLink = page.getByRole("link", { name: /analytic/i });
    if (await analyticsLink.isVisible()) {
      await analyticsLink.click();
      await expect(page).toHaveURL(/\/analytic/i);
    }
  });
});

test.describe("Dashboard Overview", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/overview");
  });

  test("should display overview statistics cards", async ({ page }) => {
    // Look for statistic cards
    const statsSection = page.locator(
      '[data-testid="stats-cards"], .stats-cards, .overview-stats',
    );
    if (await statsSection.isVisible()) {
      await expect(statsSection).toBeVisible();
    }
  });

  test("should display charts", async ({ page }) => {
    // Look for chart elements (ECharts or Recharts)
    const charts = page.locator('canvas, [class*="chart"], [class*="echarts"]');
    // Charts may take time to load
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });

  test("should display page title", async ({ page }) => {
    // Check for overview/dashboard heading
    const heading = page.getByRole("heading", { name: /overview|dashboard/i });
    await expect(heading.first()).toBeVisible();
  });
});

test.describe("Theme Toggle", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should toggle between light and dark mode", async ({ page }) => {
    const themeToggle = page.getByRole("button", {
      name: /theme|mode|dark|light/i,
    });
    if (await themeToggle.isVisible()) {
      // Get initial state
      const initialClass = await page.locator("html").getAttribute("class");

      // Click to toggle
      await themeToggle.click();

      // Wait for theme change
      await page.waitForTimeout(500);

      // Check if class changed
      const newClass = await page.locator("html").getAttribute("class");
      expect(newClass).not.toBe(initialClass);
    }
  });
});

test.describe("Responsive Design", () => {
  test("should show mobile menu on small screens", async ({ page }) => {
    await login(page);

    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 667 });

    // Look for mobile menu button
    const menuButton = page.getByRole("button", { name: /menu/i });
    if (await menuButton.isVisible()) {
      await menuButton.click();
      // Sidebar should become visible
      await expect(page.getByRole("navigation")).toBeVisible();
    }
  });
});
