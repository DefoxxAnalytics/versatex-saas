/**
 * Custom hooks for analytics data from Django API
 *
 * All hooks include organization_id in query keys to properly
 * invalidate cache when switching organizations (superuser feature).
 *
 * Filter support: Core analytics hooks now accept filters from the FilterPane
 * via the useAnalyticsFilters() hook. Filters are passed to backend APIs
 * and included in query keys for proper cache invalidation.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  analyticsAPI,
  procurementAPI,
  getOrganizationParam,
  type AnalyticsFilters,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useFilters } from "./useFilters";

/**
 * Get the current organization ID for query key inclusion.
 * Returns undefined if viewing own org (default behavior).
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

/**
 * Build name→ID lookup maps for suppliers and categories.
 * Used to convert filter names (from FilterPane) to IDs (for API).
 */
function useFilterMapping() {
  const { data: suppliers } = useSuppliersInternal();
  const { data: categories } = useCategoriesInternal();

  const supplierNameToId = useMemo(() => {
    const map = new Map<string, number>();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (suppliers as any)?.results?.forEach((s: { name: string; id: number }) =>
      map.set(s.name, s.id)
    );
    return map;
  }, [suppliers]);

  const categoryNameToId = useMemo(() => {
    const map = new Map<string, number>();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (categories as any)?.results?.forEach((c: { name: string; id: number }) =>
      map.set(c.name, c.id)
    );
    return map;
  }, [categories]);

  return { supplierNameToId, categoryNameToId };
}

// Internal hooks for filter mapping (to avoid circular dependency)
function useSuppliersInternal() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.procurement.suppliers.list(undefined, orgId),
    queryFn: async () => {
      const response = await procurementAPI.getSuppliers();
      return response.data;
    },
  });
}

function useCategoriesInternal() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.procurement.categories.list(undefined, orgId),
    queryFn: async () => {
      const response = await procurementAPI.getCategories();
      return response.data;
    },
  });
}

/**
 * Convert frontend filter state (from FilterPane) to backend API format.
 * Returns undefined if no filters are active.
 *
 * Handles:
 * - Date range (start/end)
 * - Suppliers (sends both IDs when available, and names for server-side resolution)
 * - Categories (sends both IDs when available, and names for server-side resolution)
 * - Subcategories (passed as-is, strings)
 * - Locations (passed as-is, strings)
 * - Years (converts string years to numbers)
 * - Amount range (min/max)
 *
 * Note: Both IDs and names are sent to ensure filtering works even if the
 * categories/suppliers queries haven't loaded yet. The backend will resolve
 * names to IDs server-side and combine with any provided IDs.
 */
export function useAnalyticsFilters(): AnalyticsFilters | undefined {
  const { data: filters } = useFilters();
  const { supplierNameToId, categoryNameToId } = useFilterMapping();

  return useMemo(() => {
    if (!filters) return undefined;

    const apiFilters: AnalyticsFilters = {};

    if (filters.dateRange.start) apiFilters.date_from = filters.dateRange.start;
    if (filters.dateRange.end) apiFilters.date_to = filters.dateRange.end;

    if (filters.suppliers.length > 0) {
      // Always send names for server-side resolution
      apiFilters.supplier_names = filters.suppliers;

      // Also send IDs if we have them (for efficiency)
      const ids = filters.suppliers
        .map((name) => supplierNameToId.get(name))
        .filter((id): id is number => id !== undefined);
      if (ids.length > 0) apiFilters.supplier_ids = ids;
    }

    if (filters.categories.length > 0) {
      // Always send names for server-side resolution
      apiFilters.category_names = filters.categories;

      // Also send IDs if we have them (for efficiency)
      const ids = filters.categories
        .map((name) => categoryNameToId.get(name))
        .filter((id): id is number => id !== undefined);
      if (ids.length > 0) apiFilters.category_ids = ids;
    }

    if (filters.subcategories.length > 0) {
      apiFilters.subcategories = filters.subcategories;
    }

    if (filters.locations.length > 0) {
      apiFilters.locations = filters.locations;
    }

    if (filters.years.length > 0) {
      const yearNumbers = filters.years
        .map((y) => parseInt(y, 10))
        .filter((y) => !isNaN(y));
      if (yearNumbers.length > 0) apiFilters.years = yearNumbers;
    }

    if (filters.amountRange.min !== null)
      apiFilters.min_amount = filters.amountRange.min;
    if (filters.amountRange.max !== null)
      apiFilters.max_amount = filters.amountRange.max;

    return Object.keys(apiFilters).length > 0 ? apiFilters : undefined;
  }, [filters, supplierNameToId, categoryNameToId]);
}

/**
 * Get overview statistics (total spend, supplier count, category count, etc.)
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useOverviewStats() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.overview(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get spend by category
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSpendByCategory() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.spendByCategory(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSpendByCategory(filters);
      return response.data;
    },
  });
}

/**
 * Get detailed category analysis (includes subcategories, suppliers, risk levels)
 * Use this for the Categories dashboard page.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useCategoryDetails() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.categoryDetails(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getCategoryDetails(filters);
      return response.data;
    },
  });
}

/**
 * Get spend by supplier
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSpendBySupplier() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.spendBySupplier(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSpendBySupplier(filters);
      return response.data;
    },
  });
}

/**
 * Get detailed supplier analysis (includes HHI score, concentration metrics, category diversity)
 * Use this for the Suppliers dashboard page.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSupplierDetails() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.supplierDetails(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSupplierDetails(filters);
      return response.data;
    },
  });
}

/**
 * Get monthly trend
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useMonthlyTrend(months: number = 12) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.monthlyTrend(months, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getMonthlyTrend(months, filters);
      return response.data;
    },
  });
}

/**
 * Get Pareto analysis
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useParetoAnalysis() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.pareto(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getParetoAnalysis(filters);
      return response.data;
    },
  });
}

/**
 * Get supplier drill-down data for Pareto Analysis modal
 * Fetches on-demand when a supplier is selected
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSupplierDrilldown(supplierId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.supplierDrilldown(supplierId!, orgId, filters),
    queryFn: async () => {
      if (!supplierId) return null;
      const response = await analyticsAPI.getSupplierDrilldown(supplierId, filters);
      return response.data;
    },
    enabled: !!supplierId,
  });
}

/**
 * Get category drill-down data for Overview page modal
 * Fetches on-demand when a category is selected in charts
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useCategoryDrilldown(categoryId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.categoryDrilldown(categoryId!, orgId, filters),
    queryFn: async () => {
      if (!categoryId) return null;
      const response = await analyticsAPI.getCategoryDrilldown(categoryId, filters);
      return response.data;
    },
    enabled: !!categoryId,
  });
}

/**
 * Get tail spend analysis
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useTailSpend(threshold: number = 20) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.tailSpend(threshold, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getTailSpend(threshold, filters);
      return response.data;
    },
  });
}

/**
 * Get detailed tail spend analysis with dollar threshold.
 * Use this for the TailSpend dashboard page.
 * Supports filtering by date range, suppliers, categories, and amount range.
 *
 * @param threshold - Dollar threshold for tail classification (default $50,000)
 */
export function useDetailedTailSpend(threshold: number = 50000) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.tailSpendDetailed(threshold, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getDetailedTailSpend(threshold, filters);
      return response.data;
    },
  });
}

/**
 * Get tail spend category drill-down data for TailSpend page modal.
 * Fetches vendor-level breakdown on-demand when a category is selected.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useTailSpendCategoryDrilldown(
  categoryId: number | null,
  threshold: number = 50000,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.tailSpendCategoryDrilldown(
      categoryId!,
      threshold,
      orgId,
      filters,
    ),
    queryFn: async () => {
      if (!categoryId) return null;
      const response = await analyticsAPI.getTailSpendCategoryDrilldown(
        categoryId,
        threshold,
        filters,
      );
      return response.data;
    },
    enabled: !!categoryId,
  });
}

/**
 * Get tail spend vendor drill-down data for TailSpend page modal.
 * Fetches category breakdown, locations, and monthly spend.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useTailSpendVendorDrilldown(
  supplierId: number | null,
  threshold: number = 50000,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.tailSpendVendorDrilldown(
      supplierId!,
      threshold,
      orgId,
      filters,
    ),
    queryFn: async () => {
      if (!supplierId) return null;
      const response = await analyticsAPI.getTailSpendVendorDrilldown(
        supplierId,
        threshold,
        filters,
      );
      return response.data;
    },
    enabled: !!supplierId,
  });
}

/**
 * Get spend stratification
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useStratification() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.stratification(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getStratification(filters);
      return response.data;
    },
  });
}

/**
 * Get detailed spend stratification (by spend bands)
 * Use this for the SpendStratification dashboard page
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useDetailedStratification() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.stratificationDetailed(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getDetailedStratification(filters);
      return response.data;
    },
  });
}

/**
 * Get segment drill-down data for SpendStratification modal
 * Fetches on-demand when a segment is selected
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSegmentDrilldown(segmentName: string | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.segmentDrilldown(segmentName!, orgId, filters),
    queryFn: async () => {
      if (!segmentName) return null;
      const response = await analyticsAPI.getSegmentDrilldown(segmentName, filters);
      return response.data;
    },
    enabled: !!segmentName,
  });
}

/**
 * Get spend band drill-down data for SpendStratification modal
 * Fetches on-demand when a spend band is selected
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useBandDrilldown(bandName: string | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.bandDrilldown(bandName!, orgId, filters),
    queryFn: async () => {
      if (!bandName) return null;
      const response = await analyticsAPI.getBandDrilldown(bandName, filters);
      return response.data;
    },
    enabled: !!bandName,
  });
}

/**
 * Get seasonality analysis
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSeasonality() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.seasonality(false, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSeasonality(filters);
      return response.data;
    },
  });
}

/**
 * Get detailed seasonality analysis with fiscal year support, category breakdowns,
 * seasonal indices, and savings potential calculations.
 * Use this for the Seasonality dashboard page.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useDetailedSeasonality(useFiscalYear: boolean = true) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.seasonalityDetailed(useFiscalYear, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getDetailedSeasonality(useFiscalYear, filters);
      return response.data;
    },
  });
}

/**
 * Get seasonality category drill-down data for Seasonality page modal.
 * Fetches supplier-level seasonal patterns on-demand when a category is selected.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useSeasonalityCategoryDrilldown(
  categoryId: number | null,
  useFiscalYear: boolean = true,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.seasonalityCategoryDrilldown(
      categoryId!,
      useFiscalYear,
      orgId,
      filters,
    ),
    queryFn: async () => {
      if (!categoryId) return null;
      const response = await analyticsAPI.getSeasonalityCategoryDrilldown(
        categoryId,
        useFiscalYear,
        filters,
      );
      return response.data;
    },
    enabled: !!categoryId,
  });
}

/**
 * Get year over year comparison
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useYearOverYear() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.yearOverYear(false, 0, 0, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getYearOverYear(filters);
      return response.data;
    },
  });
}

/**
 * Get detailed year over year comparison with fiscal year support,
 * category/supplier comparisons, monthly trends, and top gainers/decliners.
 * Use this for the YearOverYear dashboard page.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useDetailedYearOverYear(
  useFiscalYear: boolean = true,
  year1?: number,
  year2?: number,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.yoyDetailed(
      useFiscalYear,
      year1 ?? 0,
      year2 ?? 0,
      orgId,
      filters,
    ),
    queryFn: async () => {
      const response = await analyticsAPI.getDetailedYearOverYear(
        useFiscalYear,
        year1,
        year2,
        filters,
      );
      return response.data;
    },
  });
}

/**
 * Get YoY category drill-down data for YearOverYear page modal.
 * Fetches supplier-level YoY breakdown on-demand when a category is selected.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useYoYCategoryDrilldown(
  categoryId: number | null,
  useFiscalYear: boolean = true,
  year1?: number,
  year2?: number,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.yoyCategoryDrilldown(
      categoryId!,
      useFiscalYear,
      year1 ?? 0,
      year2 ?? 0,
      orgId,
      filters,
    ),
    queryFn: async () => {
      if (!categoryId) return null;
      const response = await analyticsAPI.getYoYCategoryDrilldown(
        categoryId,
        useFiscalYear,
        year1,
        year2,
        filters,
      );
      return response.data;
    },
    enabled: !!categoryId,
  });
}

/**
 * Get YoY supplier drill-down data for YearOverYear page modal.
 * Fetches category-level YoY breakdown on-demand when a supplier is selected.
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useYoYSupplierDrilldown(
  supplierId: number | null,
  useFiscalYear: boolean = true,
  year1?: number,
  year2?: number,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.yoySupplierDrilldown(
      supplierId!,
      useFiscalYear,
      year1 ?? 0,
      year2 ?? 0,
      orgId,
      filters,
    ),
    queryFn: async () => {
      if (!supplierId) return null;
      const response = await analyticsAPI.getYoYSupplierDrilldown(
        supplierId,
        useFiscalYear,
        year1,
        year2,
        filters,
      );
      return response.data;
    },
    enabled: !!supplierId,
  });
}

/**
 * Get consolidation opportunities
 * Supports filtering by date range, suppliers, categories, and amount range.
 */
export function useConsolidation() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.analytics.consolidation(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getConsolidation(filters);
      return response.data;
    },
  });
}

/**
 * Get all transactions
 */
export function useTransactions(params?: Record<string, unknown>) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.procurement.transactions.list(params, orgId),
    queryFn: async () => {
      const response = await procurementAPI.getTransactions(params);
      return response.data;
    },
  });
}

/**
 * Get all suppliers
 */
export function useSuppliers() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.procurement.suppliers.list(undefined, orgId),
    queryFn: async () => {
      const response = await procurementAPI.getSuppliers();
      return response.data;
    },
  });
}

/**
 * Get all categories
 */
export function useCategories() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.procurement.categories.list(undefined, orgId),
    queryFn: async () => {
      const response = await procurementAPI.getCategories();
      return response.data;
    },
  });
}
