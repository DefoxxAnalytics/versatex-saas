/**
 * Tests for Filter Hooks
 *
 * Tests the filter state management hooks that persist across tabs.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFilters, useUpdateFilters, useResetFilters } from "../useFilters";

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useFilters", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should return default filters on first load", () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: createWrapper(),
    });

    waitFor(() => {
      expect(result.current.data).toEqual({
        dateRange: { start: null, end: null },
        categories: [],
        subcategories: [],
        suppliers: [],
        locations: [],
        years: [],
        amountRange: { min: null, max: null },
      });
    });
  });

  it("should load filters from localStorage if available", () => {
    const savedFilters = {
      dateRange: { start: "2024-01-01", end: "2024-12-31" },
      categories: ["IT", "Office Supplies"],
      subcategories: [],
      suppliers: ["Acme Corp"],
      locations: [],
      years: [],
      amountRange: { min: 100, max: 10000 },
    };

    localStorage.setItem("procurement_filters", JSON.stringify(savedFilters));

    const { result } = renderHook(() => useFilters(), {
      wrapper: createWrapper(),
    });

    waitFor(() => {
      expect(result.current.data).toEqual(savedFilters);
    });
  });
});

describe("useUpdateFilters", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should update date range filter", async () => {
    const wrapper = createWrapper();
    const { result: filtersResult } = renderHook(() => useFilters(), {
      wrapper,
    });
    const { result: updateResult } = renderHook(() => useUpdateFilters(), {
      wrapper,
    });

    await act(async () => {
      await updateResult.current.mutateAsync({
        dateRange: { start: "2024-01-01", end: "2024-12-31" },
      });
    });

    await waitFor(() => {
      expect(filtersResult.current.data?.dateRange).toEqual({
        start: "2024-01-01",
        end: "2024-12-31",
      });
    });
  });

  it("should update category filter", async () => {
    const wrapper = createWrapper();
    const { result: filtersResult } = renderHook(() => useFilters(), {
      wrapper,
    });
    const { result: updateResult } = renderHook(() => useUpdateFilters(), {
      wrapper,
    });

    await act(async () => {
      await updateResult.current.mutateAsync({
        categories: ["IT", "Office Supplies"],
      });
    });

    await waitFor(() => {
      expect(filtersResult.current.data?.categories).toEqual([
        "IT",
        "Office Supplies",
      ]);
    });
  });

  it("should update supplier filter", async () => {
    const wrapper = createWrapper();
    const { result: filtersResult } = renderHook(() => useFilters(), {
      wrapper,
    });
    const { result: updateResult } = renderHook(() => useUpdateFilters(), {
      wrapper,
    });

    await act(async () => {
      await updateResult.current.mutateAsync({
        suppliers: ["Acme Corp", "TechVendor Inc"],
      });
    });

    await waitFor(() => {
      expect(filtersResult.current.data?.suppliers).toEqual([
        "Acme Corp",
        "TechVendor Inc",
      ]);
    });
  });

  it("should update amount range filter", async () => {
    const wrapper = createWrapper();
    const { result: filtersResult } = renderHook(() => useFilters(), {
      wrapper,
    });
    const { result: updateResult } = renderHook(() => useUpdateFilters(), {
      wrapper,
    });

    await act(async () => {
      await updateResult.current.mutateAsync({
        amountRange: { min: 100, max: 10000 },
      });
    });

    await waitFor(() => {
      expect(filtersResult.current.data?.amountRange).toEqual({
        min: 100,
        max: 10000,
      });
    });
  });

  it("should persist filters to localStorage", async () => {
    const wrapper = createWrapper();
    const { result: updateResult } = renderHook(() => useUpdateFilters(), {
      wrapper,
    });

    await act(async () => {
      await updateResult.current.mutateAsync({
        categories: ["IT"],
        suppliers: ["Acme Corp"],
      });
    });

    await waitFor(() => {
      const saved = JSON.parse(
        localStorage.getItem("procurement_filters") || "{}",
      );
      expect(saved.categories).toEqual(["IT"]);
      expect(saved.suppliers).toEqual(["Acme Corp"]);
    });
  });
});

describe("useResetFilters", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should reset all filters to default", async () => {
    // Set some filters first
    const savedFilters = {
      dateRange: { start: "2024-01-01", end: "2024-12-31" },
      categories: ["IT"],
      subcategories: [],
      suppliers: ["Acme Corp"],
      locations: [],
      years: [],
      amountRange: { min: 100, max: 10000 },
    };
    localStorage.setItem("procurement_filters", JSON.stringify(savedFilters));

    const wrapper = createWrapper();
    const { result: filtersResult } = renderHook(() => useFilters(), {
      wrapper,
    });
    const { result: resetResult } = renderHook(() => useResetFilters(), {
      wrapper,
    });

    await act(async () => {
      await resetResult.current.mutateAsync();
    });

    await waitFor(() => {
      expect(filtersResult.current.data).toEqual({
        dateRange: { start: null, end: null },
        categories: [],
        subcategories: [],
        suppliers: [],
        locations: [],
        years: [],
        amountRange: { min: null, max: null },
      });
    });
  });

  it("should clear localStorage on reset", async () => {
    localStorage.setItem(
      "procurement_filters",
      JSON.stringify({ categories: ["IT"] }),
    );

    const wrapper = createWrapper();
    const { result: resetResult } = renderHook(() => useResetFilters(), {
      wrapper,
    });

    await act(async () => {
      await resetResult.current.mutateAsync();
    });

    await waitFor(() => {
      const saved = localStorage.getItem("procurement_filters");
      expect(saved).toBe(null);
    });
  });
});
