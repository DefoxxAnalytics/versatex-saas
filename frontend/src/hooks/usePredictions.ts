/**
 * Custom hooks for Predictive Analytics data from Django API
 *
 * All hooks include organization_id in query keys to properly
 * invalidate cache when switching organizations (superuser feature).
 *
 * Filter support: Predictions hooks now accept filters from the FilterPane
 * via the useAnalyticsFilters() hook. Filters are passed to backend APIs
 * and included in query keys for proper cache invalidation.
 */
import { useQuery } from "@tanstack/react-query";
import { analyticsAPI, getOrganizationParam } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useAnalyticsFilters } from "./useAnalytics";
import type { TrendDirection } from "@/lib/api";

/**
 * Get the current organization ID for query key inclusion.
 * Returns undefined if viewing own org (default behavior).
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

/**
 * Get spending forecast for the next N months
 */
export function useSpendingForecast(months: number = 6) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.predictions.spendingForecast(months, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSpendingForecast(months, filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 2,
  });
}

/**
 * Get forecast for a specific category
 */
export function useCategoryForecast(categoryId: number, months: number = 6) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.predictions.categoryForecast(categoryId, months, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getCategoryForecast(
        categoryId,
        months,
        filters,
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: categoryId > 0,
  });
}

/**
 * Get forecast for a specific supplier
 */
export function useSupplierForecast(supplierId: number, months: number = 6) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.predictions.supplierForecast(supplierId, months, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getSupplierForecast(
        supplierId,
        months,
        filters,
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: supplierId > 0,
  });
}

/**
 * Get comprehensive trend analysis
 */
export function useTrendAnalysis() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.predictions.trendAnalysis(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getTrendAnalysis(filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get budget projection
 */
export function useBudgetProjection(annualBudget: number) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.predictions.budgetProjection(annualBudget, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getBudgetProjection(annualBudget, filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    enabled: annualBudget > 0,
  });
}

/**
 * Get trend direction display info
 */
export function getTrendDisplay(direction: TrendDirection): {
  label: string;
  color: string;
  bgColor: string;
  icon: "up" | "down" | "stable";
} {
  const displays = {
    increasing: {
      label: "Increasing",
      color: "text-red-600",
      bgColor: "bg-red-100",
      icon: "up" as const,
    },
    decreasing: {
      label: "Decreasing",
      color: "text-green-600",
      bgColor: "bg-green-100",
      icon: "down" as const,
    },
    stable: {
      label: "Stable",
      color: "text-blue-600",
      bgColor: "bg-blue-100",
      icon: "stable" as const,
    },
  };
  return displays[direction] || displays.stable;
}

/**
 * Format percentage change
 */
export function formatChangeRate(rate: number): string {
  const percentage = rate * 100;
  const sign = percentage >= 0 ? "+" : "";
  return `${sign}${percentage.toFixed(1)}%`;
}

/**
 * Get budget status display info
 */
export function getBudgetStatusDisplay(status: string): {
  label: string;
  color: string;
  bgColor: string;
} {
  const displays: Record<
    string,
    { label: string; color: string; bgColor: string }
  > = {
    under_budget: {
      label: "Under Budget",
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    over_budget: {
      label: "Over Budget",
      color: "text-red-600",
      bgColor: "bg-red-100",
    },
    on_track: {
      label: "On Track",
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    no_data: {
      label: "No Data",
      color: "text-gray-600",
      bgColor: "bg-gray-100",
    },
  };
  return displays[status] || displays.no_data;
}
