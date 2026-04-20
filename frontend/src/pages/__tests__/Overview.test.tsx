/**
 * Tests for Overview Page Component
 *
 * Tests the main dashboard view including:
 * - Loading state with skeleton loaders
 * - Empty data state display
 * - Summary statistics cards
 * - Chart rendering
 * - Drill-down modal functionality
 * - Permission-based admin panel link
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Overview from "../Overview";

// Mock analytics hooks
vi.mock("@/hooks/useAnalytics", () => ({
  useOverviewStats: vi.fn(),
  useSpendByCategory: vi.fn(),
  useSpendBySupplier: vi.fn(),
  useMonthlyTrend: vi.fn(),
  useCategoryDrilldown: vi.fn(() => ({ data: null, isLoading: false })),
  useSupplierDrilldown: vi.fn(() => ({ data: null, isLoading: false })),
}));

// Mock procurement data hook
vi.mock("@/hooks/useProcurementData", () => ({
  useFilteredProcurementData: vi.fn(),
}));

// Mock permission context
vi.mock("@/contexts/PermissionContext", () => ({
  usePermissions: vi.fn(),
}));

// Mock chart configs
vi.mock("@/lib/chartConfigs", () => ({
  getCategoryChartFromAPI: vi.fn(() => ({})),
  getTrendChartFromAPI: vi.fn(() => ({})),
  getSupplierChartFromAPI: vi.fn(() => ({})),
  getSpendDistributionConfig: vi.fn(() => ({})),
}));

// Mock components
vi.mock("@/components/StatCard", () => ({
  StatCard: ({
    title,
    value,
    description,
  }: {
    title: string;
    value: string | number;
    description: string;
  }) => (
    <div data-testid={`stat-card-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <div>{title}</div>
      <div>{value}</div>
      <div>{description}</div>
    </div>
  ),
}));

vi.mock("@/components/Chart", () => ({
  Chart: ({ title, description }: { title: string; description: string }) => (
    <div data-testid={`chart-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <div>{title}</div>
      <div>{description}</div>
    </div>
  ),
}));

vi.mock("@/components/SkeletonCard", () => ({
  SkeletonCard: () => <div data-testid="skeleton-card" />,
}));

vi.mock("@/components/SkeletonChart", () => ({
  SkeletonChart: () => <div data-testid="skeleton-chart" />,
}));

vi.mock("@/components/DrillDownModal", () => ({
  DrillDownModal: ({ open, title }: { open: boolean; title: string }) =>
    open ? <div data-testid="drill-down-modal">{title} Details</div> : null,
}));

import {
  useOverviewStats,
  useSpendByCategory,
  useSpendBySupplier,
  useMonthlyTrend,
} from "@/hooks/useAnalytics";
import { useFilteredProcurementData } from "@/hooks/useProcurementData";
import { usePermissions } from "@/contexts/PermissionContext";

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Mock data
const mockOverviewStats = {
  total_spend: 1500000,
  transaction_count: 500,
  supplier_count: 25,
  category_count: 10,
  avg_transaction: 3000,
};

const mockCategoryData = [
  { category: "IT Equipment", amount: 450000, count: 100 },
  { category: "Office Supplies", amount: 150000, count: 200 },
];

const mockSupplierData = [
  { supplier: "Acme Corp", amount: 500000, count: 150 },
  { supplier: "Beta Inc", amount: 250000, count: 100 },
];

const mockTrendData = [
  { month: "2024-01", amount: 125000, count: 40 },
  { month: "2024-02", amount: 130000, count: 45 },
  { month: "2024-03", amount: 140000, count: 50 },
];

const mockProcurementData = [
  {
    id: 1,
    supplier: "Acme Corp",
    category: "IT Equipment",
    amount: 5000,
    date: "2024-01-15",
    location: "New York",
  },
];

describe("Overview Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    vi.mocked(useOverviewStats).mockReturnValue({
      data: mockOverviewStats,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as ReturnType<typeof useOverviewStats>);

    vi.mocked(useSpendByCategory).mockReturnValue({
      data: mockCategoryData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as ReturnType<typeof useSpendByCategory>);

    vi.mocked(useSpendBySupplier).mockReturnValue({
      data: mockSupplierData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as ReturnType<typeof useSpendBySupplier>);

    vi.mocked(useMonthlyTrend).mockReturnValue({
      data: mockTrendData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as ReturnType<typeof useMonthlyTrend>);

    vi.mocked(useFilteredProcurementData).mockReturnValue({
      data: mockProcurementData,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
    } as unknown as ReturnType<typeof useFilteredProcurementData>);

    vi.mocked(usePermissions).mockReturnValue({
      role: "admin",
      hasPermission: vi.fn((permission) => permission === "admin_panel"),
      hasAllPermissions: vi.fn(() => true),
      hasAnyPermission: vi.fn(() => true),
      getDenialMessage: vi.fn(() => ""),
      isAtLeast: vi.fn(() => true),
      isAdmin: true,
      isManagerOrAbove: true,
      isSuperAdmin: false,
      canUploadForAnyOrg: false,
    });
  });

  describe("Loading State", () => {
    it("should display skeleton loaders while data is fetching", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useOverviewStats>);

      vi.mocked(useSpendByCategory).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useSpendByCategory>);

      vi.mocked(useSpendBySupplier).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useSpendBySupplier>);

      vi.mocked(useMonthlyTrend).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useMonthlyTrend>);

      render(<Overview />, { wrapper: createWrapper() });

      // Should show skeleton cards (4 stat cards)
      expect(screen.getAllByTestId("skeleton-card")).toHaveLength(4);
      // Should show skeleton charts (4 charts)
      expect(screen.getAllByTestId("skeleton-chart")).toHaveLength(4);
    });

    it("should display page header even during loading", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useOverviewStats>);

      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByText("Overview")).toBeInTheDocument();
      expect(
        screen.getByText("Key metrics and insights from your procurement data"),
      ).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no transaction data exists", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: { ...mockOverviewStats, transaction_count: 0 },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByText("No Data Available")).toBeInTheDocument();
    });

    it("should show admin upload link for admin users", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: { ...mockOverviewStats, transaction_count: 0 },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      vi.mocked(usePermissions).mockReturnValue({
        role: "admin",
        hasPermission: vi.fn(() => true),
        hasAllPermissions: vi.fn(() => true),
        hasAnyPermission: vi.fn(() => true),
        getDenialMessage: vi.fn(() => ""),
        isAtLeast: vi.fn(() => true),
        isAdmin: true,
        isManagerOrAbove: true,
        isSuperAdmin: false,
        canUploadForAnyOrg: false,
      });

      render(<Overview />, { wrapper: createWrapper() });

      expect(
        screen.getByText(
          "Upload your procurement data via the Admin Panel to see analytics and insights.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("Go to Admin Panel")).toBeInTheDocument();
    });

    it("should show different message for non-admin users", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: { ...mockOverviewStats, transaction_count: 0 },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      vi.mocked(usePermissions).mockReturnValue({
        role: "viewer",
        hasPermission: vi.fn(() => false),
        hasAllPermissions: vi.fn(() => false),
        hasAnyPermission: vi.fn(() => false),
        getDenialMessage: vi.fn(() => "You do not have permission"),
        isAtLeast: vi.fn(() => false),
        isAdmin: false,
        isManagerOrAbove: false,
        isSuperAdmin: false,
        canUploadForAnyOrg: false,
      });

      render(<Overview />, { wrapper: createWrapper() });

      expect(
        screen.getByText(
          "Contact an administrator to upload procurement data to see analytics and insights.",
        ),
      ).toBeInTheDocument();
      expect(screen.queryByText("Go to Admin Panel")).not.toBeInTheDocument();
    });
  });

  describe("Data Display", () => {
    it("should display page header with correct title", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByText("Overview")).toBeInTheDocument();
      expect(
        screen.getByText("Key metrics and insights from your procurement data"),
      ).toBeInTheDocument();
    });

    it("should display all four summary statistics cards", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByTestId("stat-card-total-spend")).toBeInTheDocument();
      expect(screen.getByTestId("stat-card-suppliers")).toBeInTheDocument();
      expect(screen.getByTestId("stat-card-categories")).toBeInTheDocument();
      expect(
        screen.getByTestId("stat-card-avg-transaction"),
      ).toBeInTheDocument();
    });

    it("should display formatted total spend value", () => {
      render(<Overview />, { wrapper: createWrapper() });

      // StatCard displays the formatted value
      const totalSpendCard = screen.getByTestId("stat-card-total-spend");
      expect(totalSpendCard).toHaveTextContent("$1,500,000");
    });

    it("should display supplier count", () => {
      render(<Overview />, { wrapper: createWrapper() });

      const suppliersCard = screen.getByTestId("stat-card-suppliers");
      expect(suppliersCard).toHaveTextContent("25");
    });

    it("should display category count", () => {
      render(<Overview />, { wrapper: createWrapper() });

      const categoriesCard = screen.getByTestId("stat-card-categories");
      expect(categoriesCard).toHaveTextContent("10");
    });

    it("should display formatted average transaction", () => {
      render(<Overview />, { wrapper: createWrapper() });

      const avgCard = screen.getByTestId("stat-card-avg-transaction");
      expect(avgCard).toHaveTextContent("$3,000");
    });
  });

  describe("Charts Display", () => {
    it("should display all four charts", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByTestId("chart-spend-by-category")).toBeInTheDocument();
      expect(
        screen.getByTestId("chart-spend-trend-over-time"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("chart-top-10-suppliers")).toBeInTheDocument();
      expect(
        screen.getByTestId("chart-spend-distribution"),
      ).toBeInTheDocument();
    });

    it("should display chart descriptions", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(
        screen.getByText(/Shows how your procurement budget is distributed/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Track monthly spending patterns/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Your largest vendors by total spend/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Categorizes transactions into High.*Medium.*and Low/),
      ).toBeInTheDocument();
    });
  });

  describe("Hook Integration", () => {
    it("should call useOverviewStats hook", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(useOverviewStats).toHaveBeenCalled();
    });

    it("should call useSpendByCategory hook", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(useSpendByCategory).toHaveBeenCalled();
    });

    it("should call useSpendBySupplier hook", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(useSpendBySupplier).toHaveBeenCalled();
    });

    it("should call useMonthlyTrend hook with 12 months", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(useMonthlyTrend).toHaveBeenCalledWith(12);
    });

    it("should call useFilteredProcurementData for drill-down data", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(useFilteredProcurementData).toHaveBeenCalled();
    });

    it("should call usePermissions to check admin access", () => {
      render(<Overview />, { wrapper: createWrapper() });

      expect(usePermissions).toHaveBeenCalled();
    });
  });

  describe("Edge Cases", () => {
    it("should handle zero values gracefully", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: {
          total_spend: 0,
          transaction_count: 1, // At least 1 to not trigger empty state
          supplier_count: 0,
          category_count: 0,
          avg_transaction: 0,
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      render(<Overview />, { wrapper: createWrapper() });

      const totalSpendCard = screen.getByTestId("stat-card-total-spend");
      expect(totalSpendCard).toHaveTextContent("$0");
    });

    it("should handle undefined overview stats before empty check", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: false,
      } as ReturnType<typeof useOverviewStats>);

      // Should not crash
      render(<Overview />, { wrapper: createWrapper() });

      // Since data is undefined and not explicitly showing transaction_count: 0,
      // it should show the normal view with default values
      expect(screen.getByText("Overview")).toBeInTheDocument();
    });

    it("should handle empty category data array", () => {
      vi.mocked(useSpendByCategory).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as unknown as ReturnType<typeof useSpendByCategory>);

      render(<Overview />, { wrapper: createWrapper() });

      // Chart should still render (with empty data)
      expect(screen.getByTestId("chart-spend-by-category")).toBeInTheDocument();
    });

    it("should handle empty supplier data array", () => {
      vi.mocked(useSpendBySupplier).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as unknown as ReturnType<typeof useSpendBySupplier>);

      render(<Overview />, { wrapper: createWrapper() });

      expect(screen.getByTestId("chart-top-10-suppliers")).toBeInTheDocument();
    });

    it("should handle empty trend data array", () => {
      vi.mocked(useMonthlyTrend).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as unknown as ReturnType<typeof useMonthlyTrend>);

      render(<Overview />, { wrapper: createWrapper() });

      expect(
        screen.getByTestId("chart-spend-trend-over-time"),
      ).toBeInTheDocument();
    });
  });

  describe("Currency Formatting", () => {
    it("should format large numbers correctly", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: {
          ...mockOverviewStats,
          total_spend: 15000000, // 15 million
          avg_transaction: 50000,
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      render(<Overview />, { wrapper: createWrapper() });

      const totalSpendCard = screen.getByTestId("stat-card-total-spend");
      expect(totalSpendCard).toHaveTextContent("$15,000,000");
    });

    it("should format decimal values without decimal places", () => {
      vi.mocked(useOverviewStats).mockReturnValue({
        data: {
          ...mockOverviewStats,
          total_spend: 1234567.89,
          avg_transaction: 1234.56,
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
      } as ReturnType<typeof useOverviewStats>);

      render(<Overview />, { wrapper: createWrapper() });

      // Should format without decimals
      const totalSpendCard = screen.getByTestId("stat-card-total-spend");
      expect(totalSpendCard).toHaveTextContent("$1,234,568"); // Rounded
    });
  });
});
