import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  timeout: 60000, // Increased for admin wizard tests

  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    // Admin tests project (Django Admin at port 8001)
    {
      name: "admin",
      testMatch: "**/admin-*.spec.ts",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: "http://localhost:8001",
      },
    },
  ],

  webServer: [
    // Frontend server
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    // Note: Backend (Django) at localhost:8001 is expected to be running via Docker
  ],
});
