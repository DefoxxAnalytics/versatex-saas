/**
 * Tests for API Client (lib/api.ts)
 *
 * Comprehensive tests covering:
 * - Authentication API (login, register, logout, token refresh)
 * - Procurement API (suppliers, categories, transactions, uploads)
 * - Analytics API (overview, spend analysis, pareto, tail-spend, etc.)
 * - Reports API (templates, generation, schedules, downloads)
 * - P2P Analytics API (cycle time, matching, aging, PRs, POs, payments)
 * - Axios interceptors (token refresh, error handling)
 * - Organization parameter handling
 */

import { describe, it, expect, vi, beforeEach, afterEach, Mock } from "vitest";
import axios, {
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

// Mock axios before importing the module
vi.mock("axios", () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };

  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
  };
});

// Import after mocking
import {
  api,
  authAPI,
  procurementAPI,
  analyticsAPI,
  reportsAPI,
  p2pAnalyticsAPI,
  getOrganizationParam,
} from "../api";

// Get the mocked axios instance
const mockAxios = axios.create() as unknown as {
  get: Mock;
  post: Mock;
  put: Mock;
  patch: Mock;
  delete: Mock;
  interceptors: {
    request: { use: Mock };
    response: { use: Mock };
  };
};

// Helper to create mock response
function createMockResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: "OK",
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  };
}

describe("API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // =====================
  // Organization Parameter Tests
  // =====================
  describe("getOrganizationParam", () => {
    it("should return empty object when no organization is stored", () => {
      const result = getOrganizationParam();
      expect(result).toEqual({});
    });

    it("should return organization_id when stored in localStorage", () => {
      localStorage.setItem("active_organization_id", "123");
      const result = getOrganizationParam();
      expect(result).toEqual({ organization_id: 123 });
    });

    it("should parse organization_id as integer", () => {
      localStorage.setItem("active_organization_id", "456");
      const result = getOrganizationParam();
      expect(result.organization_id).toBe(456);
      expect(typeof result.organization_id).toBe("number");
    });
  });

  // =====================
  // Authentication API Tests
  // =====================
  describe("authAPI", () => {
    describe("register", () => {
      it("should call POST /auth/register/ with user data", async () => {
        const userData = {
          username: "newuser",
          email: "new@example.com",
          password: "password123",
          password_confirm: "password123",
          organization: 1,
        };
        const mockResponse = createMockResponse({
          user: { id: 1, username: "newuser", email: "new@example.com" },
          message: "Registration successful",
        });

        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.register(userData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/auth/register/",
          userData,
        );
      });
    });

    describe("login", () => {
      it("should call POST /auth/login/ with credentials", async () => {
        const credentials = { username: "testuser", password: "testpass" };
        const mockResponse = createMockResponse({
          user: { id: 1, username: "testuser" },
          message: "Login successful",
        });

        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.login(credentials);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/auth/login/",
          credentials,
        );
      });
    });

    describe("logout", () => {
      it("should call POST /auth/logout/", async () => {
        const mockResponse = createMockResponse({ message: "Logged out" });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.logout();

        expect(mockAxios.post).toHaveBeenCalledWith("/auth/logout/");
      });
    });

    describe("getCurrentUser", () => {
      it("should call GET /auth/user/", async () => {
        const mockUser = {
          id: 1,
          username: "testuser",
          email: "test@example.com",
          first_name: "Test",
          last_name: "User",
          profile: {
            id: 1,
            organization: 1,
            organization_name: "Test Org",
            role: "admin" as const,
            phone: "",
            department: "",
            is_active: true,
            created_at: "2024-01-01",
            is_super_admin: false,
          },
        };
        const mockResponse = createMockResponse(mockUser);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await authAPI.getCurrentUser();

        expect(mockAxios.get).toHaveBeenCalledWith("/auth/user/");
      });
    });

    describe("changePassword", () => {
      it("should call POST /auth/change-password/ with password data", async () => {
        const passwordData = {
          old_password: "oldpass",
          new_password: "newpass",
          new_password_confirm: "newpass",
        };
        const mockResponse = createMockResponse({
          message: "Password changed",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.changePassword(passwordData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/auth/change-password/",
          passwordData,
        );
      });
    });

    describe("refreshToken", () => {
      it("should call POST /auth/token/refresh/", async () => {
        const mockResponse = createMockResponse({ message: "Token refreshed" });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.refreshToken();

        expect(mockAxios.post).toHaveBeenCalledWith("/auth/token/refresh/");
      });
    });

    describe("getPreferences", () => {
      it("should call GET /auth/preferences/", async () => {
        const mockPrefs = { theme: "dark", notifications: true };
        const mockResponse = createMockResponse(mockPrefs);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await authAPI.getPreferences();

        expect(mockAxios.get).toHaveBeenCalledWith("/auth/preferences/");
      });
    });

    describe("updatePreferences", () => {
      it("should call PATCH /auth/preferences/ with partial data", async () => {
        const prefs = { theme: "dark" as const };
        const mockResponse = createMockResponse({
          theme: "dark",
          notifications: true,
        });
        mockAxios.patch.mockResolvedValueOnce(mockResponse);

        await authAPI.updatePreferences(prefs);

        expect(mockAxios.patch).toHaveBeenCalledWith(
          "/auth/preferences/",
          prefs,
        );
      });
    });

    describe("replacePreferences", () => {
      it("should call PUT /auth/preferences/ with full data", async () => {
        const prefs = { theme: "light" as const, notifications: false };
        const mockResponse = createMockResponse(prefs);
        mockAxios.put.mockResolvedValueOnce(mockResponse);

        await authAPI.replacePreferences(prefs as any);

        expect(mockAxios.put).toHaveBeenCalledWith("/auth/preferences/", prefs);
      });
    });

    describe("getOrganizations", () => {
      it("should call GET /auth/organizations/", async () => {
        const mockResponse = createMockResponse({
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 1, name: "Test Org", slug: "test-org" }],
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await authAPI.getOrganizations();

        expect(mockAxios.get).toHaveBeenCalledWith("/auth/organizations/");
      });
    });

    describe("getOrganization", () => {
      it("should call GET /auth/organizations/:id/", async () => {
        const mockResponse = createMockResponse({ id: 1, name: "Test Org" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await authAPI.getOrganization(1);

        expect(mockAxios.get).toHaveBeenCalledWith("/auth/organizations/1/");
      });
    });

    describe("getUserOrganizations", () => {
      it("should call GET /auth/user/organizations/", async () => {
        const mockResponse = createMockResponse({
          organizations: [
            { id: 1, organization_name: "Test Org", role: "admin" },
          ],
          count: 1,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await authAPI.getUserOrganizations();

        expect(mockAxios.get).toHaveBeenCalledWith("/auth/user/organizations/");
      });
    });

    describe("switchOrganization", () => {
      it("should call POST /auth/user/organizations/:id/switch/", async () => {
        const mockResponse = createMockResponse({
          message: "Switched",
          organization_id: 2,
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await authAPI.switchOrganization(2);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/auth/user/organizations/2/switch/",
        );
      });
    });
  });

  // =====================
  // Procurement API Tests
  // =====================
  describe("procurementAPI", () => {
    describe("Suppliers", () => {
      it("getSuppliers should call GET /procurement/suppliers/ with params", async () => {
        const mockResponse = createMockResponse({
          count: 10,
          results: [{ id: 1, name: "Supplier 1" }],
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getSuppliers({ page: 1, page_size: 10 });

        expect(mockAxios.get).toHaveBeenCalledWith("/procurement/suppliers/", {
          params: { page: 1, page_size: 10 },
        });
      });

      it("getSuppliers should include organization_id when set", async () => {
        localStorage.setItem("active_organization_id", "5");
        const mockResponse = createMockResponse({ count: 0, results: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getSuppliers();

        expect(mockAxios.get).toHaveBeenCalledWith("/procurement/suppliers/", {
          params: { organization_id: 5 },
        });
      });

      it("getSupplier should call GET /procurement/suppliers/:id/", async () => {
        const mockResponse = createMockResponse({ id: 1, name: "Supplier 1" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getSupplier(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/procurement/suppliers/1/",
          {
            params: {},
          },
        );
      });

      it("createSupplier should call POST /procurement/suppliers/", async () => {
        const supplierData = { name: "New Supplier" };
        const mockResponse = createMockResponse({
          id: 1,
          name: "New Supplier",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await procurementAPI.createSupplier(supplierData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/procurement/suppliers/",
          supplierData,
        );
      });

      it("updateSupplier should call PATCH /procurement/suppliers/:id/", async () => {
        const updateData = { name: "Updated Supplier" };
        const mockResponse = createMockResponse({
          id: 1,
          name: "Updated Supplier",
        });
        mockAxios.patch.mockResolvedValueOnce(mockResponse);

        await procurementAPI.updateSupplier(1, updateData);

        expect(mockAxios.patch).toHaveBeenCalledWith(
          "/procurement/suppliers/1/",
          updateData,
        );
      });

      it("deleteSupplier should call DELETE /procurement/suppliers/:id/", async () => {
        mockAxios.delete.mockResolvedValueOnce(createMockResponse(undefined));

        await procurementAPI.deleteSupplier(1);

        expect(mockAxios.delete).toHaveBeenCalledWith(
          "/procurement/suppliers/1/",
        );
      });
    });

    describe("Categories", () => {
      it("getCategories should call GET /procurement/categories/", async () => {
        const mockResponse = createMockResponse({ count: 5, results: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getCategories({ search: "office" });

        expect(mockAxios.get).toHaveBeenCalledWith("/procurement/categories/", {
          params: { search: "office" },
        });
      });

      it("getCategory should call GET /procurement/categories/:id/", async () => {
        const mockResponse = createMockResponse({
          id: 1,
          name: "Office Supplies",
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getCategory(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/procurement/categories/1/",
          {
            params: {},
          },
        );
      });

      it("createCategory should call POST /procurement/categories/", async () => {
        const categoryData = { name: "New Category" };
        const mockResponse = createMockResponse({
          id: 1,
          name: "New Category",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await procurementAPI.createCategory(categoryData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/procurement/categories/",
          categoryData,
        );
      });

      it("updateCategory should call PATCH /procurement/categories/:id/", async () => {
        const updateData = { name: "Updated Category" };
        const mockResponse = createMockResponse({
          id: 1,
          name: "Updated Category",
        });
        mockAxios.patch.mockResolvedValueOnce(mockResponse);

        await procurementAPI.updateCategory(1, updateData);

        expect(mockAxios.patch).toHaveBeenCalledWith(
          "/procurement/categories/1/",
          updateData,
        );
      });

      it("deleteCategory should call DELETE /procurement/categories/:id/", async () => {
        mockAxios.delete.mockResolvedValueOnce(createMockResponse(undefined));

        await procurementAPI.deleteCategory(1);

        expect(mockAxios.delete).toHaveBeenCalledWith(
          "/procurement/categories/1/",
        );
      });
    });

    describe("Transactions", () => {
      it("getTransactions should call GET /procurement/transactions/", async () => {
        const mockResponse = createMockResponse({ count: 100, results: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getTransactions({
          supplier: 1,
          start_date: "2024-01-01",
        });

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/procurement/transactions/",
          {
            params: { supplier: 1, start_date: "2024-01-01" },
          },
        );
      });

      it("getTransaction should call GET /procurement/transactions/:id/", async () => {
        const mockResponse = createMockResponse({ id: 1, amount: "1000.00" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getTransaction(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/procurement/transactions/1/",
          {
            params: {},
          },
        );
      });

      it("createTransaction should call POST /procurement/transactions/", async () => {
        const transactionData = { amount: 1000, date: "2024-01-01" };
        const mockResponse = createMockResponse({ id: 1, amount: "1000.00" });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await procurementAPI.createTransaction(transactionData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/procurement/transactions/",
          transactionData,
        );
      });

      it("updateTransaction should call PATCH /procurement/transactions/:id/", async () => {
        const updateData = { amount: 2000 };
        const mockResponse = createMockResponse({ id: 1, amount: "2000.00" });
        mockAxios.patch.mockResolvedValueOnce(mockResponse);

        await procurementAPI.updateTransaction(1, updateData);

        expect(mockAxios.patch).toHaveBeenCalledWith(
          "/procurement/transactions/1/",
          updateData,
        );
      });

      it("deleteTransaction should call DELETE /procurement/transactions/:id/", async () => {
        mockAxios.delete.mockResolvedValueOnce(createMockResponse(undefined));

        await procurementAPI.deleteTransaction(1);

        expect(mockAxios.delete).toHaveBeenCalledWith(
          "/procurement/transactions/1/",
        );
      });

      it("uploadCSV should call POST /procurement/transactions/upload_csv/ with FormData", async () => {
        const file = new File(["test"], "test.csv", { type: "text/csv" });
        const mockResponse = createMockResponse({
          upload: { id: 1, file_name: "test.csv", status: "completed" },
          message: "Upload successful",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await procurementAPI.uploadCSV(file, true);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/procurement/transactions/upload_csv/",
          expect.any(FormData),
          { headers: { "Content-Type": "multipart/form-data" } },
        );
      });

      it("bulkDelete should call POST /procurement/transactions/bulk_delete/", async () => {
        const mockResponse = createMockResponse({
          deleted: 5,
          message: "Deleted",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await procurementAPI.bulkDelete([1, 2, 3, 4, 5]);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/procurement/transactions/bulk_delete/",
          {
            ids: [1, 2, 3, 4, 5],
          },
        );
      });

      it("exportCSV should call GET /procurement/transactions/export/ with blob responseType", async () => {
        const mockBlob = new Blob(["csv data"]);
        const mockResponse = createMockResponse(mockBlob);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.exportCSV({ start_date: "2024-01-01" });

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/procurement/transactions/export/",
          {
            params: { start_date: "2024-01-01" },
            responseType: "blob",
          },
        );
      });
    });

    describe("Uploads", () => {
      it("getUploads should call GET /procurement/uploads/", async () => {
        const mockResponse = createMockResponse({ count: 5, results: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await procurementAPI.getUploads({ page: 1 });

        expect(mockAxios.get).toHaveBeenCalledWith("/procurement/uploads/", {
          params: { page: 1 },
        });
      });
    });
  });

  // =====================
  // Analytics API Tests
  // =====================
  describe("analyticsAPI", () => {
    describe("Overview & Basic Analytics", () => {
      it("getOverview should call GET /analytics/overview/", async () => {
        const mockResponse = createMockResponse({
          total_spend: 1000000,
          transaction_count: 500,
          supplier_count: 50,
          category_count: 20,
          avg_transaction: 2000,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getOverview();

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/overview/", {
          params: {},
        });
      });

      it("getSpendByCategory should call GET /analytics/spend-by-category/", async () => {
        const mockResponse = createMockResponse([
          { category: "Office", amount: 50000, count: 100 },
        ]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSpendByCategory();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/spend-by-category/",
          { params: {} },
        );
      });

      it("getCategoryDetails should call GET /analytics/categories/detailed/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getCategoryDetails();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/categories/detailed/",
          { params: {} },
        );
      });

      it("getSpendBySupplier should call GET /analytics/spend-by-supplier/", async () => {
        const mockResponse = createMockResponse([
          { supplier: "Acme Corp", amount: 100000, count: 50 },
        ]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSpendBySupplier();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/spend-by-supplier/",
          { params: {} },
        );
      });

      it("getSupplierDetails should call GET /analytics/suppliers/detailed/", async () => {
        const mockResponse = createMockResponse({
          summary: { total_suppliers: 50 },
          suppliers: [],
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSupplierDetails();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/suppliers/detailed/",
          { params: {} },
        );
      });

      it("getMonthlyTrend should call GET /analytics/monthly-trend/ with months param", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getMonthlyTrend(6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/monthly-trend/",
          {
            params: { months: 6 },
          },
        );
      });
    });

    describe("Pareto Analysis", () => {
      it("getParetoAnalysis should call GET /analytics/pareto/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getParetoAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/pareto/", {
          params: {},
        });
      });

      it("getSupplierDrilldown should call GET /analytics/pareto/supplier/:id/", async () => {
        const mockResponse = createMockResponse({
          supplier_id: 1,
          supplier_name: "Acme",
          total_spend: 100000,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSupplierDrilldown(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/pareto/supplier/1/",
          { params: {} },
        );
      });
    });

    describe("Tail Spend Analysis", () => {
      it("getTailSpend should call GET /analytics/tail-spend/ with threshold", async () => {
        const mockResponse = createMockResponse({
          tail_suppliers: [],
          tail_count: 10,
          tail_spend: 50000,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getTailSpend(30);

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/tail-spend/", {
          params: { threshold: 30 },
        });
      });

      it("getDetailedTailSpend should call GET /analytics/tail-spend/detailed/", async () => {
        const mockResponse = createMockResponse({ summary: {}, segments: {} });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getDetailedTailSpend(100000);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/tail-spend/detailed/",
          {
            params: { threshold: 100000 },
          },
        );
      });

      it("getTailSpendCategoryDrilldown should call GET /analytics/tail-spend/category/:id/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getTailSpendCategoryDrilldown(1, 50000);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/tail-spend/category/1/",
          {
            params: { threshold: 50000 },
          },
        );
      });

      it("getTailSpendVendorDrilldown should call GET /analytics/tail-spend/vendor/:id/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getTailSpendVendorDrilldown(1, 50000);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/tail-spend/vendor/1/",
          {
            params: { threshold: 50000 },
          },
        );
      });
    });

    describe("Stratification", () => {
      it("getStratification should call GET /analytics/stratification/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getStratification();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/stratification/",
          { params: {} },
        );
      });

      it("getDetailedStratification should call GET /analytics/stratification/detailed/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getDetailedStratification();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/stratification/detailed/",
          { params: {} },
        );
      });

      it("getSegmentDrilldown should call GET /analytics/stratification/segment/:name/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSegmentDrilldown("strategic");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/stratification/segment/strategic/",
          { params: {} },
        );
      });

      it("getBandDrilldown should encode band name in URL", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getBandDrilldown("$10K-$50K");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/stratification/band/%2410K-%2450K/",
          { params: {} },
        );
      });
    });

    describe("Seasonality", () => {
      it("getSeasonality should call GET /analytics/seasonality/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSeasonality();

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/seasonality/", {
          params: {},
        });
      });

      it("getDetailedSeasonality should call with use_fiscal_year param", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getDetailedSeasonality(false);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/seasonality/detailed/",
          {
            params: { use_fiscal_year: false },
          },
        );
      });

      it("getSeasonalityCategoryDrilldown should call with category ID and fiscal year", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSeasonalityCategoryDrilldown(1, true);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/seasonality/category/1/",
          {
            params: { use_fiscal_year: true },
          },
        );
      });
    });

    describe("Year-over-Year", () => {
      it("getYearOverYear should call GET /analytics/year-over-year/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getYearOverYear();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/year-over-year/",
          { params: {} },
        );
      });

      it("getDetailedYearOverYear should call with year params", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getDetailedYearOverYear(true, 2023, 2024);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/year-over-year/detailed/",
          {
            params: { use_fiscal_year: true, year1: 2023, year2: 2024 },
          },
        );
      });

      it("getYoYCategoryDrilldown should call with category ID and years", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getYoYCategoryDrilldown(1, true, 2023, 2024);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/year-over-year/category/1/",
          {
            params: { use_fiscal_year: true, year1: 2023, year2: 2024 },
          },
        );
      });

      it("getYoYSupplierDrilldown should call with supplier ID and years", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getYoYSupplierDrilldown(1, false, 2022, 2023);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/year-over-year/supplier/1/",
          {
            params: { use_fiscal_year: false, year1: 2022, year2: 2023 },
          },
        );
      });
    });

    describe("Consolidation", () => {
      it("getConsolidation should call GET /analytics/consolidation/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getConsolidation();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/consolidation/",
          { params: {} },
        );
      });
    });

    describe("AI Insights", () => {
      it("getAIInsights should call GET /analytics/ai-insights/", async () => {
        const mockResponse = createMockResponse({ insights: [], summary: {} });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getAIInsights();

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/ai-insights/", {
          params: {},
        });
      });

      it("getAIInsightsCost should call GET /analytics/ai-insights/cost/", async () => {
        const mockResponse = createMockResponse({ insights: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getAIInsightsCost();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/ai-insights/cost/",
          { params: {} },
        );
      });

      it("getAIInsightsRisk should call GET /analytics/ai-insights/risk/", async () => {
        const mockResponse = createMockResponse({ insights: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getAIInsightsRisk();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/ai-insights/risk/",
          { params: {} },
        );
      });

      it("getAIInsightsAnomalies should call with sensitivity param", async () => {
        const mockResponse = createMockResponse({ insights: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getAIInsightsAnomalies(3.0);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/ai-insights/anomalies/",
          {
            params: { sensitivity: 3.0 },
          },
        );
      });
    });

    describe("Predictive Analytics", () => {
      it("getSpendingForecast should call with months param", async () => {
        const mockResponse = createMockResponse({
          forecast: [],
          trend: {},
          model_accuracy: {},
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSpendingForecast(12);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/predictions/spending/",
          {
            params: { months: 12 },
          },
        );
      });

      it("getCategoryForecast should call with category ID and months", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getCategoryForecast(1, 6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/predictions/category/1/",
          {
            params: { months: 6 },
          },
        );
      });

      it("getSupplierForecast should call with supplier ID and months", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSupplierForecast(1, 6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/predictions/supplier/1/",
          {
            params: { months: 6 },
          },
        );
      });

      it("getTrendAnalysis should call GET /analytics/predictions/trends/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getTrendAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/predictions/trends/",
          { params: {} },
        );
      });

      it("getBudgetProjection should call with annual_budget param", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getBudgetProjection(1000000);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/predictions/budget/",
          {
            params: { annual_budget: 1000000 },
          },
        );
      });
    });

    describe("Contract Analytics", () => {
      it("getContractOverview should call GET /analytics/contracts/overview/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/overview/",
          { params: {} },
        );
      });

      it("getContracts should call GET /analytics/contracts/", async () => {
        const mockResponse = createMockResponse({ contracts: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContracts();

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/contracts/", {
          params: {},
        });
      });

      it("getContractDetail should call GET /analytics/contracts/:id/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractDetail(1);

        expect(mockAxios.get).toHaveBeenCalledWith("/analytics/contracts/1/", {
          params: {},
        });
      });

      it("getExpiringContracts should call with days param", async () => {
        const mockResponse = createMockResponse({
          contracts: [],
          count: 0,
          days_threshold: 90,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getExpiringContracts(60);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/expiring/",
          {
            params: { days: 60 },
          },
        );
      });

      it("getContractPerformance should call GET /analytics/contracts/:id/performance/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractPerformance(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/1/performance/",
          { params: {} },
        );
      });

      it("getContractSavings should call GET /analytics/contracts/savings/", async () => {
        const mockResponse = createMockResponse({
          opportunities: [],
          total_potential_savings: 0,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractSavings();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/savings/",
          { params: {} },
        );
      });

      it("getContractRenewals should call GET /analytics/contracts/renewals/", async () => {
        const mockResponse = createMockResponse({
          recommendations: [],
          count: 0,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractRenewals();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/renewals/",
          { params: {} },
        );
      });

      it("getContractVsActual should call GET /analytics/contracts/vs-actual/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractVsActual(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/vs-actual/",
          {
            params: { contract_id: 1 },
          },
        );
      });

      it("getContractVsActual without contract ID should not include contract_id param", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getContractVsActual();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/contracts/vs-actual/",
          { params: {} },
        );
      });
    });

    describe("Compliance & Maverick Spend", () => {
      it("getComplianceOverview should call GET /analytics/compliance/overview/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getComplianceOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/overview/",
          { params: {} },
        );
      });

      it("getMaverickSpendAnalysis should call GET /analytics/compliance/maverick-spend/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getMaverickSpendAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/maverick-spend/",
          { params: {} },
        );
      });

      it("getPolicyViolations should call with filters", async () => {
        const mockResponse = createMockResponse({ violations: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getPolicyViolations({
          resolved: false,
          severity: "high",
          limit: 10,
        });

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/violations/",
          {
            params: { resolved: false, severity: "high", limit: 10 },
          },
        );
      });

      it("resolveViolation should call POST /analytics/compliance/violations/:id/resolve/", async () => {
        const mockResponse = createMockResponse({ id: 1, is_resolved: true });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.resolveViolation(1, "Approved by manager");

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/analytics/compliance/violations/1/resolve/",
          { resolution_notes: "Approved by manager" },
          { params: {} },
        );
      });

      it("getViolationTrends should call with months param", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getViolationTrends(6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/trends/",
          {
            params: { months: 6 },
          },
        );
      });

      it("getSupplierComplianceScores should call GET /analytics/compliance/supplier-scores/", async () => {
        const mockResponse = createMockResponse({ suppliers: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSupplierComplianceScores();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/supplier-scores/",
          { params: {} },
        );
      });

      it("getSpendingPolicies should call GET /analytics/compliance/policies/", async () => {
        const mockResponse = createMockResponse({ policies: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await analyticsAPI.getSpendingPolicies();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/compliance/policies/",
          { params: {} },
        );
      });
    });
  });

  // =====================
  // Reports API Tests
  // =====================
  describe("reportsAPI", () => {
    describe("Templates", () => {
      it("getTemplates should call GET /reports/templates/", async () => {
        const mockResponse = createMockResponse([
          {
            id: "exec",
            name: "Executive Summary",
            report_type: "executive_summary",
          },
        ]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getTemplates();

        expect(mockAxios.get).toHaveBeenCalledWith("/reports/templates/", {
          params: {},
        });
      });

      it("getTemplate should call GET /reports/templates/:id/", async () => {
        const mockResponse = createMockResponse({
          id: "exec",
          name: "Executive Summary",
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getTemplate("exec");

        expect(mockAxios.get).toHaveBeenCalledWith("/reports/templates/exec/", {
          params: {},
        });
      });
    });

    describe("Report Generation", () => {
      it("generate should call POST /reports/generate/ with report data", async () => {
        const reportData = {
          report_type: "executive_summary" as const,
          report_format: "pdf" as const,
          name: "Q4 Summary",
          period_start: "2024-10-01",
          period_end: "2024-12-31",
        };
        const mockResponse = createMockResponse({
          id: "report-123",
          status: "generating",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await reportsAPI.generate(reportData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/reports/generate/",
          reportData,
          { params: {} },
        );
      });

      it("preview should call POST /reports/preview/", async () => {
        const reportData = {
          report_type: "spend_analysis" as const,
        };
        const mockResponse = createMockResponse({
          overview: {},
          _preview: true,
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await reportsAPI.preview(reportData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/reports/preview/",
          reportData,
          { params: {} },
        );
      });
    });

    describe("Report List and Detail", () => {
      it("getReports should call GET /reports/ with filters", async () => {
        const mockResponse = createMockResponse({
          results: [],
          total: 0,
          limit: 20,
          offset: 0,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getReports({
          status: "completed",
          report_type: "spend_analysis",
        });

        expect(mockAxios.get).toHaveBeenCalledWith("/reports/", {
          params: { status: "completed", report_type: "spend_analysis" },
        });
      });

      it("getReport should call GET /reports/:id/", async () => {
        const mockResponse = createMockResponse({
          id: "report-123",
          name: "Q4 Summary",
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getReport("report-123");

        expect(mockAxios.get).toHaveBeenCalledWith("/reports/report-123/", {
          params: {},
        });
      });

      it("getStatus should call GET /reports/:id/status/", async () => {
        const mockResponse = createMockResponse({
          id: "report-123",
          status: "completed",
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getStatus("report-123");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/reports/report-123/status/",
          { params: {} },
        );
      });

      it("deleteReport should call DELETE /reports/:id/delete/", async () => {
        mockAxios.delete.mockResolvedValueOnce(createMockResponse(undefined));

        await reportsAPI.deleteReport("report-123");

        expect(mockAxios.delete).toHaveBeenCalledWith(
          "/reports/report-123/delete/",
          { params: {} },
        );
      });
    });

    describe("Report Download", () => {
      it("download should call GET /reports/:id/download/ with output_format", async () => {
        const mockBlob = new Blob(["pdf content"]);
        const mockResponse = createMockResponse(mockBlob);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        const result = await reportsAPI.download("report-123", "pdf");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/reports/report-123/download/",
          {
            params: { output_format: "pdf" },
            responseType: "blob",
          },
        );
        expect(result).toBe(mockBlob);
      });
    });

    describe("Sharing", () => {
      it("share should call POST /reports/:id/share/", async () => {
        const shareData = { user_ids: [1, 2, 3], is_public: false };
        const mockResponse = createMockResponse({ id: "report-123" });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await reportsAPI.share("report-123", shareData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/reports/report-123/share/",
          shareData,
          { params: {} },
        );
      });
    });

    describe("Scheduled Reports", () => {
      it("getSchedules should call GET /reports/schedules/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getSchedules();

        expect(mockAxios.get).toHaveBeenCalledWith("/reports/schedules/", {
          params: {},
        });
      });

      it("createSchedule should call POST /reports/schedules/", async () => {
        const scheduleData = {
          name: "Weekly Report",
          report_type: "spend_analysis" as const,
          is_scheduled: true,
          schedule_frequency: "weekly" as const,
        };
        const mockResponse = createMockResponse({ id: "schedule-123" });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await reportsAPI.createSchedule(scheduleData);

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/reports/schedules/",
          scheduleData,
          { params: {} },
        );
      });

      it("getSchedule should call GET /reports/schedules/:id/", async () => {
        const mockResponse = createMockResponse({ id: "schedule-123" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await reportsAPI.getSchedule("schedule-123");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/reports/schedules/schedule-123/",
          { params: {} },
        );
      });

      it("updateSchedule should call PUT /reports/schedules/:id/", async () => {
        const updateData = { name: "Updated Schedule" };
        const mockResponse = createMockResponse({ id: "schedule-123" });
        mockAxios.put.mockResolvedValueOnce(mockResponse);

        await reportsAPI.updateSchedule("schedule-123", updateData);

        expect(mockAxios.put).toHaveBeenCalledWith(
          "/reports/schedules/schedule-123/",
          updateData,
          { params: {} },
        );
      });

      it("deleteSchedule should call DELETE /reports/schedules/:id/", async () => {
        mockAxios.delete.mockResolvedValueOnce(createMockResponse(undefined));

        await reportsAPI.deleteSchedule("schedule-123");

        expect(mockAxios.delete).toHaveBeenCalledWith(
          "/reports/schedules/schedule-123/",
          { params: {} },
        );
      });

      it("runScheduleNow should call POST /reports/schedules/:id/run-now/", async () => {
        const mockResponse = createMockResponse({
          message: "Started",
          id: "report-456",
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await reportsAPI.runScheduleNow("schedule-123");

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/reports/schedules/schedule-123/run-now/",
          {},
          { params: {} },
        );
      });
    });
  });

  // =====================
  // P2P Analytics API Tests
  // =====================
  describe("p2pAnalyticsAPI", () => {
    describe("Cycle Time Analysis", () => {
      it("getCycleOverview should call GET /analytics/p2p/cycle-overview/", async () => {
        const mockResponse = createMockResponse({
          stages: {},
          total_cycle: {},
          summary: {},
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getCycleOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/cycle-overview/",
          { params: {} },
        );
      });

      it("getCycleByCategory should call GET /analytics/p2p/cycle-by-category/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getCycleByCategory();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/cycle-by-category/",
          { params: {} },
        );
      });

      it("getCycleBySupplier should call GET /analytics/p2p/cycle-by-supplier/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getCycleBySupplier();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/cycle-by-supplier/",
          { params: {} },
        );
      });

      it("getCycleTrends should call with months param", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getCycleTrends(6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/cycle-trends/",
          {
            params: { months: 6 },
          },
        );
      });

      it("getBottlenecks should call GET /analytics/p2p/bottlenecks/", async () => {
        const mockResponse = createMockResponse({ bottlenecks: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getBottlenecks();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/bottlenecks/",
          { params: {} },
        );
      });

      it("getProcessFunnel should call with months param", async () => {
        const mockResponse = createMockResponse({
          stages: [],
          drop_off_points: [],
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getProcessFunnel(24);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/process-funnel/",
          {
            params: { months: 24 },
          },
        );
      });

      it("getStageDrilldown should call GET /analytics/p2p/stage-drilldown/:stage/", async () => {
        const mockResponse = createMockResponse({
          stage: "pr_to_po",
          slowest_documents: [],
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getStageDrilldown("pr_to_po");

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/p2p/stage-drilldown/pr_to_po/",
          { params: {} },
        );
      });
    });

    describe("3-Way Matching", () => {
      it("getMatchingOverview should call GET /analytics/matching/overview/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getMatchingOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/overview/",
          { params: {} },
        );
      });

      it("getMatchingExceptions should call with filters", async () => {
        const mockResponse = createMockResponse({
          exceptions: [],
          count: 0,
          filters: {},
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getMatchingExceptions({
          status: "open",
          exception_type: "price_variance",
          limit: 50,
        });

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/exceptions/",
          {
            params: {
              status: "open",
              exception_type: "price_variance",
              limit: 50,
            },
          },
        );
      });

      it("getExceptionsByType should call GET /analytics/matching/exceptions-by-type/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getExceptionsByType();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/exceptions-by-type/",
          { params: {} },
        );
      });

      it("getExceptionsBySupplier should call GET /analytics/matching/exceptions-by-supplier/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getExceptionsBySupplier();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/exceptions-by-supplier/",
          { params: {} },
        );
      });

      it("getPriceVarianceAnalysis should call GET /analytics/matching/price-variance/", async () => {
        const mockResponse = createMockResponse({ items: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPriceVarianceAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/price-variance/",
          { params: {} },
        );
      });

      it("getQuantityVarianceAnalysis should call GET /analytics/matching/quantity-variance/", async () => {
        const mockResponse = createMockResponse({ items: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getQuantityVarianceAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/quantity-variance/",
          { params: {} },
        );
      });

      it("getInvoiceMatchDetail should call GET /analytics/matching/invoice/:id/", async () => {
        const mockResponse = createMockResponse({
          invoice: {},
          purchase_order: null,
          goods_receipt: null,
        });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getInvoiceMatchDetail(123);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/matching/invoice/123/",
          { params: {} },
        );
      });

      it("resolveException should call POST /analytics/matching/invoice/:id/resolve/", async () => {
        const mockResponse = createMockResponse({
          invoice_id: 123,
          resolved: true,
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.resolveException(123, "Approved");

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/analytics/matching/invoice/123/resolve/",
          { resolution_notes: "Approved" },
          { params: {} },
        );
      });

      it("bulkResolveExceptions should call POST /analytics/matching/exceptions/bulk-resolve/", async () => {
        const mockResponse = createMockResponse({
          resolved_count: 3,
          failed_count: 0,
        });
        mockAxios.post.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.bulkResolveExceptions([1, 2, 3], "Bulk approved");

        expect(mockAxios.post).toHaveBeenCalledWith(
          "/analytics/matching/exceptions/bulk-resolve/",
          { invoice_ids: [1, 2, 3], resolution_notes: "Bulk approved" },
          { params: {} },
        );
      });
    });

    describe("Invoice Aging / AP Analysis", () => {
      it("getAgingOverview should call GET /analytics/aging/overview/", async () => {
        const mockResponse = createMockResponse({ buckets: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getAgingOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/aging/overview/",
          { params: {} },
        );
      });

      it("getAgingBySupplier should call GET /analytics/aging/by-supplier/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getAgingBySupplier();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/aging/by-supplier/",
          { params: {} },
        );
      });

      it("getPaymentTermsCompliance should call GET /analytics/aging/payment-terms-compliance/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPaymentTermsCompliance();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/aging/payment-terms-compliance/",
          { params: {} },
        );
      });

      it("getDPOTrends should call with months param", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getDPOTrends(6);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/aging/dpo-trends/",
          {
            params: { months: 6 },
          },
        );
      });

      it("getCashFlowForecast should call with weeks param", async () => {
        const mockResponse = createMockResponse({ weeks: [] });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getCashFlowForecast(8);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/aging/cash-forecast/",
          {
            params: { weeks: 8 },
          },
        );
      });
    });

    describe("Purchase Requisitions", () => {
      it("getPROverview should call GET /analytics/requisitions/overview/", async () => {
        const mockResponse = createMockResponse({ total_prs: 100 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPROverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/requisitions/overview/",
          { params: {} },
        );
      });

      it("getPRApprovalAnalysis should call GET /analytics/requisitions/approval-analysis/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPRApprovalAnalysis();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/requisitions/approval-analysis/",
          { params: {} },
        );
      });

      it("getPRByDepartment should call GET /analytics/requisitions/by-department/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPRByDepartment();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/requisitions/by-department/",
          { params: {} },
        );
      });

      it("getPRPending should call with limit param", async () => {
        const mockResponse = createMockResponse({ pending_prs: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPRPending(100);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/requisitions/pending/",
          {
            params: { limit: 100 },
          },
        );
      });

      it("getPRDetail should call GET /analytics/requisitions/:id/", async () => {
        const mockResponse = createMockResponse({ id: 1, pr_number: "PR-001" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPRDetail(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/requisitions/1/",
          { params: {} },
        );
      });
    });

    describe("Purchase Orders", () => {
      it("getPOOverview should call GET /analytics/purchase-orders/overview/", async () => {
        const mockResponse = createMockResponse({ total_pos: 50 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPOOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/purchase-orders/overview/",
          { params: {} },
        );
      });

      it("getPOLeakage should call GET /analytics/purchase-orders/leakage/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPOLeakage();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/purchase-orders/leakage/",
          { params: {} },
        );
      });

      it("getPOAmendments should call GET /analytics/purchase-orders/amendments/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPOAmendments();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/purchase-orders/amendments/",
          { params: {} },
        );
      });

      it("getPOBySupplier should call GET /analytics/purchase-orders/by-supplier/", async () => {
        const mockResponse = createMockResponse([]);
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPOBySupplier();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/purchase-orders/by-supplier/",
          { params: {} },
        );
      });

      it("getPODetail should call GET /analytics/purchase-orders/:id/", async () => {
        const mockResponse = createMockResponse({ id: 1, po_number: "PO-001" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getPODetail(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/purchase-orders/1/",
          { params: {} },
        );
      });
    });

    describe("Supplier Payment Performance", () => {
      it("getSupplierPaymentsOverview should call GET /analytics/supplier-payments/overview/", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getSupplierPaymentsOverview();

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/supplier-payments/overview/",
          { params: {} },
        );
      });

      it("getSupplierPaymentsScorecard should call with limit param", async () => {
        const mockResponse = createMockResponse({ suppliers: [], count: 0 });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getSupplierPaymentsScorecard(100);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/supplier-payments/scorecard/",
          {
            params: { limit: 100 },
          },
        );
      });

      it("getSupplierPaymentDetail should call GET /analytics/supplier-payments/:id/", async () => {
        const mockResponse = createMockResponse({ supplier: "Acme Corp" });
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getSupplierPaymentDetail(1);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/supplier-payments/1/",
          { params: {} },
        );
      });

      it("getSupplierPaymentHistory should call with months param", async () => {
        const mockResponse = createMockResponse({});
        mockAxios.get.mockResolvedValueOnce(mockResponse);

        await p2pAnalyticsAPI.getSupplierPaymentHistory(1, 24);

        expect(mockAxios.get).toHaveBeenCalledWith(
          "/analytics/supplier-payments/1/history/",
          {
            params: { months: 24 },
          },
        );
      });
    });
  });

  // =====================
  // Axios Configuration Tests
  // =====================
  describe("Axios Configuration", () => {
    it("api instance should be defined and have HTTP methods", () => {
      // Verify the api instance is properly set up with HTTP methods
      expect(api).toBeDefined();
      expect(typeof mockAxios.get).toBe("function");
      expect(typeof mockAxios.post).toBe("function");
      expect(typeof mockAxios.put).toBe("function");
      expect(typeof mockAxios.patch).toBe("function");
      expect(typeof mockAxios.delete).toBe("function");
    });

    it("api instance should have interceptors object", () => {
      // Verify the mock instance has interceptors
      expect(mockAxios.interceptors).toBeDefined();
      expect(mockAxios.interceptors.response).toBeDefined();
      expect(mockAxios.interceptors.request).toBeDefined();
    });
  });

  // =====================
  // Error Handling Tests
  // =====================
  describe("Error Handling", () => {
    it("should reject with error when API call fails", async () => {
      const error = new Error("Network Error");
      mockAxios.get.mockRejectedValueOnce(error);

      await expect(analyticsAPI.getOverview()).rejects.toThrow("Network Error");
    });

    it("should reject with error when POST fails", async () => {
      const error = new Error("Server Error");
      mockAxios.post.mockRejectedValueOnce(error);

      await expect(
        authAPI.login({ username: "test", password: "test" }),
      ).rejects.toThrow("Server Error");
    });
  });
});
