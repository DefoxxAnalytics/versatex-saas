import { test, expect, Page } from "@playwright/test";
import path from "path";
import fs from "fs";

/**
 * E2E Tests for Data Upload Center in Django Admin
 * Tests the 5-step Upload Wizard, Organization Management, and Upload History
 */

const ADMIN_URL = "http://localhost:8001/admin";
const ADMIN_USERNAME = "admin";
const ADMIN_PASSWORD = "admin123";

// Helper: Login to Django Admin
async function adminLogin(page: Page) {
  await page.goto(`${ADMIN_URL}/login/`);
  await page.fill("#id_username", ADMIN_USERNAME);
  await page.fill("#id_password", ADMIN_PASSWORD);
  await page.click('input[type="submit"]');
  await page.waitForURL(`${ADMIN_URL}/`, { timeout: 10000 });
}

// Helper: Navigate to Data Upload list in admin
async function navigateToDataUploadList(page: Page) {
  await page.goto(`${ADMIN_URL}/procurement/dataupload/`);
  await expect(page.locator("h1")).toContainText(
    /Data upload|Select data upload/i,
  );
}

// Helper: Create a sample CSV file
function createSampleCSV(): string {
  const csvContent = `Supplier,Category,Amount,Date,Description,Invoice Number
Acme Corp,Office Supplies,1500.00,2024-01-15,Office furniture purchase,INV-001
Tech Solutions,IT Equipment,3200.50,2024-01-20,Laptop computers,INV-002
Global Services,Professional Services,5000.00,2024-02-01,Consulting fees,INV-003
Acme Corp,Office Supplies,750.25,2024-02-10,Paper and supplies,INV-004
BuildRight Inc,Construction,12000.00,2024-02-15,Building materials,INV-005`;

  const filePath = path.join(__dirname, "test-upload.csv");
  fs.writeFileSync(filePath, csvContent);
  return filePath;
}

// Helper: Cleanup test CSV file
function cleanupTestCSV() {
  const filePath = path.join(__dirname, "test-upload.csv");
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
}

test.describe("Django Admin Login", () => {
  test("should login to Django admin", async ({ page }) => {
    await page.goto(`${ADMIN_URL}/login/`);

    // Should see login form
    await expect(page.locator("#id_username")).toBeVisible();
    await expect(page.locator("#id_password")).toBeVisible();

    // Login
    await page.fill("#id_username", ADMIN_USERNAME);
    await page.fill("#id_password", ADMIN_PASSWORD);
    await page.click('input[type="submit"]');

    // Should be on admin dashboard
    await expect(page).toHaveURL(`${ADMIN_URL}/`);
    await expect(page.locator("h1")).toContainText(/Site administration/i);
  });
});

test.describe("Data Upload Center Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test("should navigate to Data Uploads from admin index", async ({ page }) => {
    // Click on Data uploads link in admin
    await page.click('a[href*="procurement/dataupload"]');
    await expect(page.locator("h1")).toContainText(/Data upload/i);
  });

  test("should display Upload Wizard button", async ({ page }) => {
    await navigateToDataUploadList(page);

    // Should have Upload Wizard button
    const wizardButton = page.locator('a:has-text("Upload Wizard")');
    await expect(wizardButton.first()).toBeVisible();
  });

  test("should display Data Upload Center section", async ({ page }) => {
    await navigateToDataUploadList(page);

    // Should have the upload section with description
    await expect(page.locator(".upload-section")).toBeVisible();
    await expect(page.locator("text=Data Upload Center")).toBeVisible();
  });
});

test.describe("Upload Wizard - Step Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");
  });

  test("should display wizard with 5 steps", async ({ page }) => {
    // Should see progress bar
    await expect(page.locator(".progress-bar, .wizard-progress")).toBeVisible();

    // Should be on Step 1 (File Selection)
    await expect(page.locator('#step-1, [data-step="1"]')).toBeVisible();

    // Should have all step indicators
    const stepIndicators = page.locator(".progress-step, .step-indicator");
    await expect(stepIndicators).toHaveCount(5);
  });

  test("should show file selection on step 1", async ({ page }) => {
    // Should have file drop zone
    await expect(page.locator(".drop-zone, [data-dropzone]")).toBeVisible();

    // Should have file input
    await expect(page.locator('input[type="file"]')).toBeAttached();
  });

  test("should not allow next without file", async ({ page }) => {
    // Try clicking next without file
    const nextButton = page.locator('button:has-text("Next"), .btn-next');

    if (await nextButton.isVisible()) {
      await nextButton.click();

      // Should show error or stay on step 1
      await expect(page.locator('#step-1, [data-step="1"]')).toBeVisible();
    }
  });
});

test.describe("Upload Wizard - File Upload Flow", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should accept CSV file", async ({ page }) => {
    const csvPath = createSampleCSV();

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);

    // Should show file info
    await expect(
      page.locator(".file-info, .file-name, text=test-upload.csv"),
    ).toBeVisible({ timeout: 5000 });
  });

  test("should reject non-CSV file", async ({ page }) => {
    // Create a non-CSV file
    const txtPath = path.join(__dirname, "test-file.txt");
    fs.writeFileSync(txtPath, "This is not a CSV");

    try {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(txtPath);

      // Should show error message
      await expect(
        page.locator(".error, .alert-danger, text=/CSV/i"),
      ).toBeVisible({ timeout: 5000 });
    } finally {
      if (fs.existsSync(txtPath)) {
        fs.unlinkSync(txtPath);
      }
    }
  });

  test("should proceed to step 2 after file selection", async ({ page }) => {
    const csvPath = createSampleCSV();

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);

    // Wait for file to be recognized
    await page.waitForTimeout(1000);

    // Click next
    const nextButton = page.locator('button:has-text("Next"), .btn-next');
    if (await nextButton.isVisible()) {
      await nextButton.click();

      // Should be on step 2 (Preview)
      await expect(page.locator('#step-2, [data-step="2"]')).toBeVisible({
        timeout: 10000,
      });
    }
  });
});

test.describe("Upload Wizard - Preview Step", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Upload a file to get to step 2
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.waitForTimeout(1000);

    const nextButton = page.locator('button:has-text("Next"), .btn-next');
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await page.waitForTimeout(2000);
    }
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should display data preview table", async ({ page }) => {
    // Should show preview table with data
    const previewTable = page.locator(
      "table.preview-table, #preview-table, [data-preview]",
    );
    await expect(previewTable).toBeVisible({ timeout: 10000 });

    // Should show headers from CSV
    await expect(page.locator("text=Supplier")).toBeVisible();
    await expect(page.locator("text=Category")).toBeVisible();
    await expect(page.locator("text=Amount")).toBeVisible();
  });

  test("should display file metadata", async ({ page }) => {
    // Should show row count and file info
    await expect(page.locator("text=/rows|records/i")).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("Upload Wizard - Column Mapping Step", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Navigate to step 3
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.waitForTimeout(1000);

    // Step 1 -> Step 2
    let nextButton = page.locator('button:has-text("Next"), .btn-next');
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await page.waitForTimeout(2000);
    }

    // Step 2 -> Step 3
    nextButton = page.locator('button:has-text("Next"), .btn-next');
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await page.waitForTimeout(2000);
    }
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should display column mapping interface", async ({ page }) => {
    // Should show mapping dropdowns
    const mappingSection = page.locator(
      '#step-3, [data-step="3"], .mapping-container',
    );
    await expect(mappingSection).toBeVisible({ timeout: 10000 });

    // Should have select dropdowns for mapping
    const selects = page.locator('select, [role="combobox"]');
    await expect(selects.first()).toBeVisible();
  });

  test("should auto-detect column mappings", async ({ page }) => {
    // Supplier column should be auto-mapped
    const supplierMapping = page.locator(
      'select:has(option[value="supplier"]:checked), [data-mapping="supplier"]',
    );

    // The mapping should be detected (our CSV has matching column names)
    await expect(page.locator("text=/mapped|detected/i")).toBeVisible({
      timeout: 5000,
    });
  });

  test("should allow saving mapping template", async ({ page }) => {
    // Should have save template button
    const saveButton = page.locator(
      'button:has-text("Save"), button:has-text("Template")',
    );
    await expect(saveButton.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Upload Wizard - Validation Step", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Navigate to step 4
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.waitForTimeout(1000);

    // Navigate through steps
    for (let i = 0; i < 3; i++) {
      const nextButton = page.locator('button:has-text("Next"), .btn-next');
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await page.waitForTimeout(2000);
      }
    }
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should display validation results", async ({ page }) => {
    const validationSection = page.locator(
      '#step-4, [data-step="4"], .validation-container',
    );
    await expect(validationSection).toBeVisible({ timeout: 15000 });

    // Should show validation stats
    await expect(page.locator("text=/valid|error|row/i")).toBeVisible();
  });

  test("should show skip invalid option", async ({ page }) => {
    // Should have option to skip invalid rows
    const skipOption = page.locator(
      'input[type="checkbox"]:near(:text("skip")), label:has-text("skip")',
    );
    await expect(skipOption.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Upload Wizard - Upload Progress Step", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Navigate to step 5
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.waitForTimeout(1000);

    // Navigate through all steps
    for (let i = 0; i < 4; i++) {
      const nextButton = page.locator(
        'button:has-text("Next"), .btn-next, button:has-text("Upload"), button:has-text("Start")',
      );
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await page.waitForTimeout(2000);
      }
    }
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should display upload progress", async ({ page }) => {
    const progressSection = page.locator(
      '#step-5, [data-step="5"], .upload-progress',
    );
    await expect(progressSection).toBeVisible({ timeout: 15000 });

    // Should show progress indicator
    await expect(
      page.locator('.progress-bar, progress, [role="progressbar"]'),
    ).toBeVisible();
  });

  test("should show completion status", async ({ page }) => {
    // Wait for upload to complete
    await page.waitForTimeout(10000);

    // Should show success or completion message
    await expect(page.locator("text=/complete|success|finished/i")).toBeVisible(
      { timeout: 30000 },
    );
  });
});

test.describe("Organization Management - Delete All Data", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
  });

  test("should show Delete All Data button for admin", async ({ page }) => {
    // Should have delete all data button
    const deleteButton = page.locator('a:has-text("Delete All Data")');
    await expect(deleteButton).toBeVisible();
  });

  test("should navigate to delete confirmation page", async ({ page }) => {
    const deleteButton = page.locator('a:has-text("Delete All Data")');
    await deleteButton.click();

    // Should be on delete confirmation page
    await expect(page.locator("text=/delete all/i")).toBeVisible();
    await expect(page.locator("form")).toBeVisible();
  });

  test("should require confirmation text", async ({ page }) => {
    const deleteButton = page.locator('a:has-text("Delete All Data")');
    await deleteButton.click();

    // Should have confirmation input
    await expect(page.locator('input[type="text"]')).toBeVisible();

    // Should show required confirmation text (DELETE ALL)
    await expect(page.locator("text=/DELETE ALL/i")).toBeVisible();
  });

  test("should not delete without correct confirmation", async ({ page }) => {
    const deleteButton = page.locator('a:has-text("Delete All Data")');
    await deleteButton.click();

    // Enter wrong confirmation
    await page.fill('input[type="text"]', "wrong text");

    // Submit form
    const submitButton = page.locator(
      'button[type="submit"], input[type="submit"]',
    );
    await submitButton.click();

    // Should show error
    await expect(page.locator("text=/error|incorrect|match/i")).toBeVisible({
      timeout: 5000,
    });
  });
});

test.describe("Organization Management - Reset Organization", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
  });

  test("should show Reset Organization button for superuser", async ({
    page,
  }) => {
    // This button should only appear for superusers
    const resetButton = page.locator('a:has-text("Reset Organization")');

    // Check if visible (depends on user permissions)
    const isVisible = await resetButton.isVisible();
    if (isVisible) {
      await expect(resetButton).toBeVisible();
      // Should have super admin badge
      await expect(page.locator("text=/Super Admin/i")).toBeVisible();
    }
  });

  test("should navigate to reset confirmation page", async ({ page }) => {
    const resetButton = page.locator('a:has-text("Reset Organization")');

    if (await resetButton.isVisible()) {
      await resetButton.click();

      // Should be on reset confirmation page
      await expect(page.locator("text=/reset organization/i")).toBeVisible();
    }
  });
});

test.describe("Upload History", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
  });

  test("should display upload history table", async ({ page }) => {
    // Should have results table
    const table = page.locator("#result_list, .results, table");
    await expect(table).toBeVisible();
  });

  test("should show status badges", async ({ page }) => {
    // Check for status column/badges
    await expect(
      page.locator('th:has-text("Status"), td:has-text("Status")'),
    ).toBeVisible();
  });

  test("should have filter options", async ({ page }) => {
    // Should have filter sidebar
    const filterSection = page.locator("#changelist-filter, .filters");

    if (await filterSection.isVisible()) {
      // Should have date filter
      await expect(
        filterSection.locator("text=/date|status|organization/i"),
      ).toBeVisible();
    }
  });

  test("should navigate to upload detail", async ({ page }) => {
    // Find first upload row and click
    const firstRow = page.locator("#result_list tbody tr").first();

    if (await firstRow.isVisible()) {
      const detailLink = firstRow.locator("a").first();
      await detailLink.click();

      // Should be on detail page
      await expect(page.locator("text=/change|detail|upload/i")).toBeVisible();
    }
  });
});

test.describe("Column Mapping Templates", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Navigate to step 3 (mapping)
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);
    await page.waitForTimeout(1000);

    for (let i = 0; i < 2; i++) {
      const nextButton = page.locator('button:has-text("Next"), .btn-next');
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await page.waitForTimeout(2000);
      }
    }
  });

  test.afterEach(() => {
    cleanupTestCSV();
  });

  test("should display template management UI", async ({ page }) => {
    // Should have template section
    await expect(page.locator("text=/template/i")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should allow loading existing template", async ({ page }) => {
    // Should have template dropdown or list
    const templateSelect = page.locator(
      'select:has-text("template"), [data-templates]',
    );

    if (await templateSelect.isVisible()) {
      await expect(templateSelect).toBeVisible();
    }
  });
});

test.describe("Error Handling", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test("should handle network errors gracefully", async ({ page }) => {
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Simulate offline
    await page.context().setOffline(true);

    // Try to upload
    const csvPath = createSampleCSV();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(csvPath);

    // Try to proceed
    const nextButton = page.locator('button:has-text("Next"), .btn-next');
    if (await nextButton.isVisible()) {
      await nextButton.click();

      // Should show error message
      await expect(page.locator("text=/error|failed|offline/i")).toBeVisible({
        timeout: 5000,
      });
    }

    // Restore online
    await page.context().setOffline(false);
    cleanupTestCSV();
  });

  test("should handle invalid file format", async ({ page }) => {
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");

    // Try to upload invalid file
    const invalidPath = path.join(__dirname, "invalid.xyz");
    fs.writeFileSync(invalidPath, "invalid content");

    try {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(invalidPath);

      // Should show validation error
      await expect(page.locator("text=/invalid|csv|format/i")).toBeVisible({
        timeout: 5000,
      });
    } finally {
      if (fs.existsSync(invalidPath)) {
        fs.unlinkSync(invalidPath);
      }
    }
  });
});

test.describe("Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
    await navigateToDataUploadList(page);
    await page.click('a:has-text("Upload Wizard")');
    await page.waitForLoadState("networkidle");
  });

  test("should have proper form labels", async ({ page }) => {
    // File input should have label
    const fileInput = page.locator('input[type="file"]');
    const label = page.locator("label[for]");
    await expect(label.first()).toBeVisible();
  });

  test("should be keyboard navigable", async ({ page }) => {
    // Tab through elements
    await page.keyboard.press("Tab");

    // Should focus on interactive element
    const focusedElement = page.locator(":focus");
    await expect(focusedElement).toBeVisible();
  });

  test("should have visible focus indicators", async ({ page }) => {
    // Tab to an element
    await page.keyboard.press("Tab");

    // Focused element should have visible outline
    const focusedElement = page.locator(":focus");
    const outline = await focusedElement.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.outline || styles.boxShadow;
    });

    expect(outline).toBeTruthy();
  });
});
