import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { applyFilters } from "@/lib/analytics";
import type { Filters } from "./useFilters";
import {
  procurementAPI,
  getOrganizationParam,
  type Transaction,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

/**
 * ProcurementRecord interface for frontend analytics
 * Data is now fetched from the backend API (no more IndexedDB)
 */
export interface ProcurementRecord {
  supplier: string;
  category: string;
  subcategory: string;
  amount: number;
  date: string;
  location: string;
  year?: number;
  spendBand?: string;
}

/**
 * Get the current organization ID for query key inclusion.
 * Returns undefined if viewing own org (default behavior).
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

/**
 * Transform backend Transaction to frontend ProcurementRecord
 */
function transformTransaction(tx: Transaction): ProcurementRecord {
  // Extract year from date
  const dateObj = new Date(tx.date);
  const year = !isNaN(dateObj.getTime()) ? dateObj.getFullYear() : undefined;

  return {
    supplier: tx.supplier_name,
    category: tx.category_name,
    subcategory: tx.subcategory || "Unspecified",
    amount: parseFloat(tx.amount),
    date: tx.date,
    location: tx.location || "Unknown",
    year,
    spendBand: tx.spend_band || undefined,
  };
}

/**
 * Hook to access procurement data from the backend API
 * Returns RAW UNFILTERED data - use this for:
 * - Populating filter options (categories, suppliers, locations, years)
 * - Dashboard statistics
 * - Any component that needs to see all data
 *
 * For filtered data, use useFilteredProcurementData() instead.
 *
 * NOTE: Data is now fetched from PostgreSQL via Django API.
 * Upload data via Django Admin Panel at /admin/procurement/dataupload/upload-csv/
 */
export function useProcurementData() {
  const orgId = getOrgKeyPart();
  return useQuery<ProcurementRecord[], Error>({
    queryKey: queryKeys.procurement.data(orgId),
    queryFn: async (): Promise<ProcurementRecord[]> => {
      try {
        // Fetch transactions from the backend API
        // Note: This fetches a subset for drill-down functionality.
        // Summary statistics should use backend analytics API hooks instead.
        const response = await procurementAPI.getTransactions({
          page_size: 10000,
        });
        const transactions = response.data.results;

        // Transform backend format to frontend format
        return transactions.map(transformTransaction);
      } catch (error) {
        // Only log in development
        if (import.meta.env.DEV) {
          console.error("Failed to load data from API:", error);
        }
        return [];
      }
    },
    staleTime: 5 * 60 * 1000, // Data becomes stale after 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
  });
}

/**
 * Hook to access FILTERED procurement data
 * Automatically applies active filters from the filter pane
 *
 * Uses TanStack Query for efficient caching - filtered data is computed once
 * and shared across all components. Cache is invalidated when filters or
 * raw data change.
 *
 * Use this hook in analysis pages that should respect filter selections:
 * - Overview page
 * - Categories page
 * - Suppliers page
 * - Pareto Analysis page
 * - etc.
 *
 * Do NOT use this in:
 * - FilterPane (needs raw data to show all options)
 *
 * @returns Filtered procurement records based on active filters
 */
export function useFilteredProcurementData() {
  const queryClient = useQueryClient();
  const {
    data: rawData = [] as ProcurementRecord[],
    isLoading: rawLoading,
    isError: rawError,
  } = useProcurementData();

  const orgId = getOrgKeyPart();

  // Set up event listener to invalidate query when filters change
  useEffect(() => {
    const handleFilterUpdate = () => {
      // Invalidate the filtered data query to trigger re-computation
      queryClient.invalidateQueries({
        queryKey: queryKeys.procurement.filtered(orgId),
      });
    };

    window.addEventListener("filtersUpdated", handleFilterUpdate);

    return () => {
      window.removeEventListener("filtersUpdated", handleFilterUpdate);
    };
  }, [queryClient]);

  // Use TanStack Query to cache filtered data
  const {
    data: filteredData = [] as ProcurementRecord[],
    isLoading: filterLoading,
    isError: filterError,
  } = useQuery<ProcurementRecord[], Error>({
    queryKey: [...queryKeys.procurement.filtered(orgId), rawData.length],
    queryFn: (): ProcurementRecord[] => {
      // Read filters from localStorage
      try {
        const stored = localStorage.getItem("procurement_filters");
        if (!stored || !rawData || rawData.length === 0) {
          return rawData as ProcurementRecord[];
        }

        const filters = JSON.parse(stored) as Filters;
        return applyFilters(rawData as ProcurementRecord[], filters);
      } catch (error) {
        // Only log in development
        if (import.meta.env.DEV) {
          console.error("Failed to apply filters:", error);
        }
        return rawData as ProcurementRecord[];
      }
    },
    staleTime: Infinity, // Data only becomes stale when explicitly invalidated
    gcTime: Infinity, // Keep in cache indefinitely
    enabled: !rawLoading && !rawError, // Only run when raw data is ready
  });

  return {
    data: filteredData as ProcurementRecord[],
    isLoading: rawLoading || filterLoading,
    isError: rawError || filterError,
  };
}

/**
 * Hook to refresh procurement data from the API
 * Call this after data changes (e.g., after admin uploads new data)
 */
export function useRefreshData() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      // Just invalidate the query - TanStack Query will refetch
      await queryClient.invalidateQueries({
        queryKey: queryKeys.procurement.all,
      });
    },
  });
}

/**
 * Hook to get summary statistics from procurement data
 */
export function useProcurementStats() {
  const { data = [] as ProcurementRecord[] } = useProcurementData();
  const records = data as ProcurementRecord[];

  const totalSpend = records.reduce(
    (sum: number, record: ProcurementRecord) => sum + record.amount,
    0,
  );
  const uniqueSuppliers = new Set(
    records.map((r: ProcurementRecord) => r.supplier),
  ).size;
  const uniqueCategories = new Set(
    records.map((r: ProcurementRecord) => r.category),
  ).size;
  const recordCount = records.length;

  return {
    totalSpend,
    uniqueSuppliers,
    uniqueCategories,
    recordCount,
  };
}

// Re-export ProcurementRecord type for backwards compatibility
export type { ProcurementRecord as ProcurementRecordType };
