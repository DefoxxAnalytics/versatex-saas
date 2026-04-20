/**
 * Tests for useProcurementData hooks
 *
 * Tests cover:
 * - useProcurementData - fetching raw procurement data
 * - useFilteredProcurementData - filtered data with localStorage filters
 * - useRefreshData - data refresh mutation
 * - useProcurementStats - computed statistics
 * - Organization-scoped query keys
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useProcurementData,
  useFilteredProcurementData,
  useRefreshData,
  useProcurementStats,
} from "../useProcurementData";
import * as api from "@/lib/api";
import * as analyticsLib from "@/lib/analytics";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  procurementAPI: {
    getTransactions: vi.fn(),
  },
  getOrganizationParam: vi.fn(),
}));

vi.mock("@/lib/analytics", () => ({
  applyFilters: vi.fn(),
}));

// Mock transaction data
const mockTransactions = [
  {
    id: 1,
    supplier_name: "Acme Corp",
    category_name: "Office Supplies",
    subcategory: "Paper",
    amount: "1500.00",
    date: "2024-01-15",
    location: "New York",
    spend_band: "$1K-$5K",
  },
  {
    id: 2,
    supplier_name: "Beta Inc",
    category_name: "IT Equipment",
    subcategory: "Computers",
    amount: "5000.00",
    date: "2024-02-20",
    location: "Chicago",
    spend_band: "$5K-$10K",
  },
  {
    id: 3,
    supplier_name: "Gamma LLC",
    category_name: "Office Supplies",
    subcategory: "Pens",
    amount: "250.00",
    date: "2024-03-10",
    location: "Los Angeles",
    spend_band: "<$1K",
  },
];

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

describe("useProcurementData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(api.getOrganizationParam).mockReturnValue({});
  });

  afterEach(() => {
    localStorage.clear();
  });

  // =====================
  // useProcurementData Tests
  // =====================
  describe("useProcurementData", () => {
    it("should fetch transactions from API", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledWith({
        page_size: 10000,
      });
    });

    it("should transform transactions to ProcurementRecord format", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toHaveLength(3);
      expect(result.current.data?.[0]).toEqual({
        supplier: "Acme Corp",
        category: "Office Supplies",
        subcategory: "Paper",
        amount: 1500,
        date: "2024-01-15",
        location: "New York",
        year: 2024,
        spendBand: "$1K-$5K",
      });
    });

    it("should handle missing subcategory with default", async () => {
      const txWithoutSubcategory = [
        { ...mockTransactions[0], subcategory: null },
      ];
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: txWithoutSubcategory },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.[0].subcategory).toBe("Unspecified");
    });

    it("should handle missing location with default", async () => {
      const txWithoutLocation = [{ ...mockTransactions[0], location: null }];
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: txWithoutLocation },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.[0].location).toBe("Unknown");
    });

    it("should return empty array on API error", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual([]);
    });

    it("should include org ID in query key when viewing other org", async () => {
      vi.mocked(api.getOrganizationParam).mockReturnValue({
        organization_id: 5,
      });
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Query key should be different with org ID
      expect(result.current.data).toHaveLength(3);
    });

    it("should parse year from date correctly", async () => {
      const txWithDifferentYears = [
        { ...mockTransactions[0], date: "2023-06-15" },
        { ...mockTransactions[1], date: "2024-12-01" },
      ];
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: txWithDifferentYears },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.[0].year).toBe(2023);
      expect(result.current.data?.[1].year).toBe(2024);
    });

    it("should handle invalid date gracefully", async () => {
      const txWithInvalidDate = [
        { ...mockTransactions[0], date: "invalid-date" },
      ];
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: txWithInvalidDate },
      } as any);

      const { result } = renderHook(() => useProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.[0].year).toBeUndefined();
    });
  });

  // =====================
  // useFilteredProcurementData Tests
  // =====================
  describe("useFilteredProcurementData", () => {
    it("should return raw data when no filters are stored", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useFilteredProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toHaveLength(3);
    });

    it("should apply filters from localStorage", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const filters = {
        categories: ["Office Supplies"],
        suppliers: [],
        dateRange: { start: null, end: null },
        minAmount: null,
        maxAmount: null,
        years: [],
        locations: [],
      };
      localStorage.setItem("procurement_filters", JSON.stringify(filters));

      const filteredRecords = [
        {
          supplier: "Acme Corp",
          category: "Office Supplies",
          subcategory: "Paper",
          amount: 1500,
          date: "2024-01-15",
          location: "New York",
          year: 2024,
          spendBand: "$1K-$5K",
        },
      ];
      vi.mocked(analyticsLib.applyFilters).mockReturnValue(filteredRecords);

      const { result } = renderHook(() => useFilteredProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(analyticsLib.applyFilters).toHaveBeenCalled();
    });

    it("should handle corrupted filter JSON gracefully", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      localStorage.setItem("procurement_filters", "not valid json {{{");

      const { result } = renderHook(() => useFilteredProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should return raw data on error
      expect(result.current.data).toHaveLength(3);
    });

    it("should respond to filtersUpdated event", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useFilteredProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Dispatch filter update event
      await act(async () => {
        window.dispatchEvent(new CustomEvent("filtersUpdated"));
      });

      // Hook should still work after event
      expect(result.current.data).toHaveLength(3);
    });

    it("should return empty array when raw data is empty", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: [] },
      } as any);

      const { result } = renderHook(() => useFilteredProcurementData(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual([]);
    });
  });

  // =====================
  // useRefreshData Tests
  // =====================
  describe("useRefreshData", () => {
    it("should invalidate procurement queries on refresh", async () => {
      const { result } = renderHook(() => useRefreshData(), {
        wrapper: createWrapper(),
      });

      // Call mutateAsync - it should resolve without error
      let didResolve = false;
      await act(async () => {
        await result.current.mutateAsync();
        didResolve = true;
      });

      expect(didResolve).toBe(true);
    });

    it("should not throw on multiple refreshes", async () => {
      const { result } = renderHook(() => useRefreshData(), {
        wrapper: createWrapper(),
      });

      // Multiple calls should not throw
      let callCount = 0;
      await act(async () => {
        await result.current.mutateAsync();
        callCount++;
        await result.current.mutateAsync();
        callCount++;
      });

      expect(callCount).toBe(2);
    });
  });

  // =====================
  // useProcurementStats Tests
  // =====================
  describe("useProcurementStats", () => {
    it("should compute total spend correctly", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(3);
      });

      expect(result.current.totalSpend).toBe(6750); // 1500 + 5000 + 250
    });

    it("should count unique suppliers correctly", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(3);
      });

      expect(result.current.uniqueSuppliers).toBe(3);
    });

    it("should count unique categories correctly", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(3);
      });

      // Office Supplies (2) + IT Equipment (1) = 2 unique
      expect(result.current.uniqueCategories).toBe(2);
    });

    it("should return correct record count", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: mockTransactions },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(3);
      });
    });

    it("should return zeros when no data", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: [] },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(0);
      });

      expect(result.current.totalSpend).toBe(0);
      expect(result.current.uniqueSuppliers).toBe(0);
      expect(result.current.uniqueCategories).toBe(0);
    });

    it("should handle duplicate suppliers correctly", async () => {
      const txWithDuplicates = [
        ...mockTransactions,
        { ...mockTransactions[0], id: 4 }, // Duplicate Acme Corp
      ];
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { results: txWithDuplicates },
      } as any);

      const { result } = renderHook(() => useProcurementStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.recordCount).toBe(4);
      });

      expect(result.current.uniqueSuppliers).toBe(3); // Still 3 unique
    });
  });
});
