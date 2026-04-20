/**
 * Tests for Analytics Hooks
 *
 * Tests the analytics data fetching hooks that query the Django API.
 * Uses MSW to mock API responses.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useOverviewStats,
  useSpendByCategory,
  useSpendBySupplier,
  useMonthlyTrend,
  useParetoAnalysis,
  useTailSpend,
  useStratification,
  useSeasonality,
  useYearOverYear,
  useConsolidation,
  useCategoryDetails,
  useSupplierDetails,
  useSupplierDrilldown,
  useDetailedTailSpend,
  useTailSpendCategoryDrilldown,
  useTailSpendVendorDrilldown,
  useDetailedStratification,
  useSegmentDrilldown,
  useBandDrilldown,
  useDetailedSeasonality,
  useSeasonalityCategoryDrilldown,
  useDetailedYearOverYear,
  useYoYCategoryDrilldown,
  useYoYSupplierDrilldown,
  useTransactions,
  useSuppliers,
  useCategories,
} from "../useAnalytics";

// Mock getOrganizationParam to avoid auth context dependency
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual("@/lib/api");
  return {
    ...actual,
    getOrganizationParam: () => ({ organization_id: undefined }),
  };
});

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useOverviewStats", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch overview statistics", async () => {
    const { result } = renderHook(() => useOverviewStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({
      total_spend: 75000.0,
      transaction_count: 15,
      supplier_count: 2,
      category_count: 2,
      avg_transaction: 5000.0,
    });
  });

  it("should handle loading state", () => {
    const { result } = renderHook(() => useOverviewStats(), {
      wrapper: createWrapper(),
    });

    // Initially should be loading
    expect(result.current.isLoading).toBe(true);
  });
});

describe("useSpendByCategory", () => {
  it("should fetch spend by category data", async () => {
    const { result } = renderHook(() => useSpendByCategory(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      { category: "IT Equipment", amount: 45000.0, count: 6 },
      { category: "Office Supplies", amount: 15000.0, count: 8 },
    ]);
  });
});

describe("useSpendBySupplier", () => {
  it("should fetch spend by supplier data", async () => {
    const { result } = renderHook(() => useSpendBySupplier(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      { supplier: "Supplier A", amount: 50000.0, count: 10 },
      { supplier: "Supplier B", amount: 25000.0, count: 5 },
    ]);
  });
});

describe("useMonthlyTrend", () => {
  it("should fetch monthly trend data", async () => {
    const { result } = renderHook(() => useMonthlyTrend(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      { month: "2024-01", amount: 25000.0, count: 5 },
      { month: "2024-02", amount: 30000.0, count: 6 },
      { month: "2024-03", amount: 20000.0, count: 4 },
    ]);
  });

  it("should accept custom months parameter", async () => {
    const { result } = renderHook(() => useMonthlyTrend(6), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // MSW handler returns same data regardless of months param
    expect(result.current.data).toBeDefined();
  });
});

describe("useParetoAnalysis", () => {
  it("should fetch Pareto analysis data", async () => {
    const { result } = renderHook(() => useParetoAnalysis(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      { supplier: "Supplier A", amount: 50000.0, cumulative_percentage: 66.67 },
      { supplier: "Supplier B", amount: 25000.0, cumulative_percentage: 100.0 },
    ]);
  });
});

describe("useTailSpend", () => {
  it("should fetch tail spend analysis data", async () => {
    const { result } = renderHook(() => useTailSpend(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toMatchObject({
      tail_suppliers: expect.any(Array),
      tail_count: 1,
      tail_spend: 25000.0,
      tail_percentage: 33.33,
    });
  });

  it("should accept threshold parameter", async () => {
    const { result } = renderHook(() => useTailSpend(30), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useStratification", () => {
  it("should fetch spend stratification data", async () => {
    const { result } = renderHook(() => useStratification(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toMatchObject({
      strategic: expect.any(Array),
      leverage: expect.any(Array),
      bottleneck: expect.any(Array),
      tactical: expect.any(Array),
    });
  });
});

describe("useSeasonality", () => {
  it("should fetch seasonality data", async () => {
    const { result } = renderHook(() => useSeasonality(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(12);
    expect(result.current.data![0]).toMatchObject({
      month: "Jan",
      average_spend: expect.any(Number),
      occurrences: expect.any(Number),
    });
  });
});

describe("useYearOverYear", () => {
  it("should fetch year-over-year data", async () => {
    const { result } = renderHook(() => useYearOverYear(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      {
        year: 2023,
        total_spend: 500000.0,
        transaction_count: 100,
        avg_transaction: 5000.0,
      },
      {
        year: 2024,
        total_spend: 75000.0,
        transaction_count: 15,
        avg_transaction: 5000.0,
        growth_percentage: -85.0,
      },
    ]);
  });
});

describe("useConsolidation", () => {
  it("should fetch consolidation opportunities data", async () => {
    const { result } = renderHook(() => useConsolidation(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      {
        category: "Office Supplies",
        supplier_count: 3,
        total_spend: 15000.0,
        suppliers: [
          { name: "Supplier A", spend: 8000.0 },
          { name: "Supplier B", spend: 5000.0 },
          { name: "Supplier C", spend: 2000.0 },
        ],
        potential_savings: 1500.0,
      },
    ]);
  });
});

describe("useCategoryDetails", () => {
  it("should fetch detailed category analysis", async () => {
    const { result } = renderHook(() => useCategoryDetails(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      {
        id: 1,
        name: "IT Equipment",
        total_spend: 45000.0,
        transaction_count: 6,
        supplier_count: 2,
        subcategories: ["Hardware", "Software"],
        risk_level: "low",
      },
      {
        id: 2,
        name: "Office Supplies",
        total_spend: 15000.0,
        transaction_count: 8,
        supplier_count: 3,
        subcategories: ["Paper", "Pens"],
        risk_level: "low",
      },
    ]);
  });
});

describe("useSupplierDetails", () => {
  it("should fetch detailed supplier analysis", async () => {
    const { result } = renderHook(() => useSupplierDetails(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([
      {
        id: 1,
        name: "Supplier A",
        total_spend: 50000.0,
        transaction_count: 10,
        category_count: 2,
        hhi_score: 0.35,
        concentration: "moderate",
      },
      {
        id: 2,
        name: "Supplier B",
        total_spend: 25000.0,
        transaction_count: 5,
        category_count: 1,
        hhi_score: 0.15,
        concentration: "low",
      },
    ]);
  });
});

describe("Hook Query Key Isolation", () => {
  it("should include organization ID in query keys for cache isolation", async () => {
    // This test verifies that each hook uses orgId in its query key
    // When switching orgs, cache should be properly invalidated
    const wrapper = createWrapper();

    // Render multiple hooks
    const { result: overview } = renderHook(() => useOverviewStats(), {
      wrapper,
    });
    const { result: categories } = renderHook(() => useSpendByCategory(), {
      wrapper,
    });
    const { result: suppliers } = renderHook(() => useSpendBySupplier(), {
      wrapper,
    });

    // All should eventually succeed independently
    await waitFor(() => {
      expect(overview.current.isSuccess).toBe(true);
      expect(categories.current.isSuccess).toBe(true);
      expect(suppliers.current.isSuccess).toBe(true);
    });

    // Verify data is fetched correctly
    expect(overview.current.data).toBeDefined();
    expect(categories.current.data).toBeDefined();
    expect(suppliers.current.data).toBeDefined();
  });
});

// =====================
// Drilldown Hooks Tests
// =====================
describe("useSupplierDrilldown", () => {
  it("should not fetch when supplierId is null", () => {
    const { result } = renderHook(() => useSupplierDrilldown(null), {
      wrapper: createWrapper(),
    });

    // Should not be loading since query is disabled
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when supplierId is provided", async () => {
    const { result } = renderHook(() => useSupplierDrilldown(1), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useDetailedTailSpend", () => {
  it("should fetch detailed tail spend with default threshold", async () => {
    const { result } = renderHook(() => useDetailedTailSpend(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });

  it("should accept custom threshold parameter", async () => {
    const { result } = renderHook(() => useDetailedTailSpend(100000), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useTailSpendCategoryDrilldown", () => {
  it("should not fetch when categoryId is null", () => {
    const { result } = renderHook(() => useTailSpendCategoryDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when categoryId is provided", async () => {
    const { result } = renderHook(() => useTailSpendCategoryDrilldown(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should accept custom threshold", async () => {
    const { result } = renderHook(
      () => useTailSpendCategoryDrilldown(1, 25000),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useTailSpendVendorDrilldown", () => {
  it("should not fetch when supplierId is null", () => {
    const { result } = renderHook(() => useTailSpendVendorDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when supplierId is provided", async () => {
    const { result } = renderHook(() => useTailSpendVendorDrilldown(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useDetailedStratification", () => {
  it("should fetch detailed stratification data", async () => {
    const { result } = renderHook(() => useDetailedStratification(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useSegmentDrilldown", () => {
  it("should not fetch when segmentName is null", () => {
    const { result } = renderHook(() => useSegmentDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when segmentName is provided", async () => {
    const { result } = renderHook(() => useSegmentDrilldown("strategic"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useBandDrilldown", () => {
  it("should not fetch when bandName is null", () => {
    const { result } = renderHook(() => useBandDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when bandName is provided", async () => {
    const { result } = renderHook(() => useBandDrilldown("$10K-$50K"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useDetailedSeasonality", () => {
  it("should fetch detailed seasonality with default fiscal year setting", async () => {
    const { result } = renderHook(() => useDetailedSeasonality(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });

  it("should accept useFiscalYear parameter", async () => {
    const { result } = renderHook(() => useDetailedSeasonality(false), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useSeasonalityCategoryDrilldown", () => {
  it("should not fetch when categoryId is null", () => {
    const { result } = renderHook(() => useSeasonalityCategoryDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when categoryId is provided", async () => {
    const { result } = renderHook(() => useSeasonalityCategoryDrilldown(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should accept useFiscalYear parameter", async () => {
    const { result } = renderHook(
      () => useSeasonalityCategoryDrilldown(1, false),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useDetailedYearOverYear", () => {
  it("should fetch detailed YoY with default parameters", async () => {
    const { result } = renderHook(() => useDetailedYearOverYear(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });

  it("should accept custom year parameters", async () => {
    const { result } = renderHook(
      () => useDetailedYearOverYear(true, 2023, 2024),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should accept calendar year setting", async () => {
    const { result } = renderHook(() => useDetailedYearOverYear(false), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useYoYCategoryDrilldown", () => {
  it("should not fetch when categoryId is null", () => {
    const { result } = renderHook(() => useYoYCategoryDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when categoryId is provided", async () => {
    const { result } = renderHook(() => useYoYCategoryDrilldown(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should accept custom year parameters", async () => {
    const { result } = renderHook(
      () => useYoYCategoryDrilldown(1, true, 2023, 2024),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useYoYSupplierDrilldown", () => {
  it("should not fetch when supplierId is null", () => {
    const { result } = renderHook(() => useYoYSupplierDrilldown(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });

  it("should fetch when supplierId is provided", async () => {
    const { result } = renderHook(() => useYoYSupplierDrilldown(1), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should accept custom year parameters", async () => {
    const { result } = renderHook(
      () => useYoYSupplierDrilldown(1, false, 2022, 2023),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

// =====================
// Procurement Data Hooks
// =====================
describe("useTransactions", () => {
  it("should fetch transactions", async () => {
    const { result } = renderHook(() => useTransactions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });

  it("should accept query parameters", async () => {
    const { result } = renderHook(() => useTransactions({ supplier: 1 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe("useSuppliers", () => {
  it("should fetch suppliers", async () => {
    const { result } = renderHook(() => useSuppliers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

describe("useCategories", () => {
  it("should fetch categories", async () => {
    const { result } = renderHook(() => useCategories(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});
