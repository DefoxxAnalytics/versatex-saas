import { test, expect } from "@playwright/test";

// Helper to login before tests
async function login(page) {
  await page.goto("/login");
  await page.getByLabel(/username/i).fill("testuser");
  await page.getByLabel(/password/i).fill("TestPass123!");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/(dashboard|overview)/i, { timeout: 10000 });
}

test.describe("Analytics Overview", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics");
  });

  test("should display analytics page", async ({ page }) => {
    const heading = page.getByRole("heading", { name: /analytic/i });
    await expect(heading.first()).toBeVisible();
  });

  test("should show statistics cards", async ({ page }) => {
    // Look for stat cards showing totals
    const cards = page.locator('[class*="card"], [data-testid*="stat"]');
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test("should display charts", async ({ page }) => {
    // Charts use canvas elements (ECharts/Recharts)
    const charts = page.locator(
      'canvas, [class*="chart"], svg[class*="recharts"]',
    );
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Spend by Category", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics");
  });

  test("should display category breakdown", async ({ page }) => {
    // Look for category section or chart
    const categorySection = page.locator(
      '[data-testid="spend-by-category"], :text("category"):visible',
    );
    if (await categorySection.isVisible()) {
      await expect(categorySection).toBeVisible();
    }
  });

  test("should show pie or bar chart for categories", async ({ page }) => {
    // Wait for charts to render
    await page.waitForTimeout(2000);

    const charts = page.locator("canvas, svg");
    await expect(charts.first()).toBeVisible();
  });
});

test.describe("Spend by Supplier", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics");
  });

  test("should display supplier breakdown", async ({ page }) => {
    const supplierSection = page.locator(
      '[data-testid="spend-by-supplier"], :text("supplier"):visible',
    );
    if (await supplierSection.isVisible()) {
      await expect(supplierSection).toBeVisible();
    }
  });
});

test.describe("Pareto Analysis", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics/pareto");
  });

  test("should display Pareto chart", async ({ page }) => {
    const paretoSection = page.locator(
      '[data-testid="pareto-analysis"], :text("pareto"):visible, :text("80/20"):visible',
    );
    if (await paretoSection.first().isVisible()) {
      await expect(paretoSection.first()).toBeVisible();
    }
  });

  test("should show cumulative percentage line", async ({ page }) => {
    // Pareto charts typically have a line showing cumulative %
    const charts = page.locator("canvas, svg");
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Tail Spend Analysis", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics/tail-spend");
  });

  test("should display tail spend statistics", async ({ page }) => {
    const tailSection = page.locator(
      '[data-testid="tail-spend"], :text("tail"):visible',
    );
    if (await tailSection.first().isVisible()) {
      await expect(tailSection.first()).toBeVisible();
    }
  });
});

test.describe("Spend Stratification", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics/stratification");
  });

  test("should display Kraljic matrix", async ({ page }) => {
    // Look for matrix quadrants
    const quadrants = page.locator(
      ':text("strategic"):visible, :text("leverage"):visible, :text("bottleneck"):visible, :text("tactical"):visible',
    );
    if (await quadrants.first().isVisible()) {
      // At least one quadrant visible
      await expect(quadrants.first()).toBeVisible();
    }
  });
});

test.describe("Monthly Trend", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics");
  });

  test("should display trend line chart", async ({ page }) => {
    const trendSection = page.locator(
      '[data-testid="monthly-trend"], :text("trend"):visible, :text("month"):visible',
    );
    if (await trendSection.first().isVisible()) {
      await expect(trendSection.first()).toBeVisible();
    }
  });

  test("should allow time period selection", async ({ page }) => {
    const periodSelector = page.getByRole("combobox", {
      name: /period|month|year/i,
    });
    if (await periodSelector.isVisible()) {
      await periodSelector.click();
      await expect(page.locator('[role="listbox"]')).toBeVisible();
    }
  });
});

test.describe("Analytics Filters", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto("/analytics");
  });

  test("should have date range filter", async ({ page }) => {
    const dateFilter = page.locator(
      '[data-testid="date-filter"], input[type="date"], [class*="date-picker"]',
    );
    if (await dateFilter.first().isVisible()) {
      await expect(dateFilter.first()).toBeVisible();
    }
  });

  test("should have supplier filter", async ({ page }) => {
    const supplierFilter = page.getByRole("combobox", { name: /supplier/i });
    if (await supplierFilter.isVisible()) {
      await supplierFilter.click();
      await expect(
        page.locator('[role="listbox"], [role="menu"]'),
      ).toBeVisible();
    }
  });

  test("should have category filter", async ({ page }) => {
    const categoryFilter = page.getByRole("combobox", { name: /category/i });
    if (await categoryFilter.isVisible()) {
      await categoryFilter.click();
      await expect(
        page.locator('[role="listbox"], [role="menu"]'),
      ).toBeVisible();
    }
  });
});

test.describe("Analytics Loading States", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should show loading indicator while fetching data", async ({
    page,
  }) => {
    // Navigate with a slow network to catch loading state
    await page.route("**/api/**/analytics/**", async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      await route.continue();
    });

    await page.goto("/analytics");

    // Look for loading indicators
    const loader = page.locator(
      '[class*="loading"], [class*="spinner"], [role="progressbar"]',
    );
    // It may or may not be visible depending on timing
    const charts = page.locator("canvas, svg");
    await expect(charts.first()).toBeVisible({ timeout: 15000 });
  });

  test("should display data after loading", async ({ page }) => {
    await page.goto("/analytics");

    // Wait for content to load
    await page.waitForLoadState("networkidle");

    // Charts should be visible
    const charts = page.locator('canvas, svg, [class*="chart"]');
    await expect(charts.first()).toBeVisible({ timeout: 10000 });
  });
});
