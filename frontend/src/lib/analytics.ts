import type { ProcurementRecord } from "../hooks/useProcurementData";
import type { Filters } from "../hooks/useFilters";

/**
 * Analytics utilities for procurement data
 *
 * Note: Most analytics calculations are now handled by backend APIs.
 * This module contains only client-side filtering for drill-down functionality.
 *
 * Security: All inputs are validated, no unsafe operations
 * Performance: Optimized for large datasets with efficient algorithms
 */

/**
 * Format a number as USD currency
 *
 * @param amount - The numeric amount to format
 * @returns Formatted currency string (e.g., "$1,234,567")
 *
 * @example
 * ```ts
 * formatCurrency(1234567.89) // Returns "$1,234,568"
 * formatCurrency(0) // Returns "$0"
 * ```
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format a number as a percentage
 *
 * @param value - The numeric value (e.g., 0.75 for 75%)
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted percentage string (e.g., "75.0%")
 *
 * @example
 * ```ts
 * formatPercent(0.756) // Returns "75.6%"
 * formatPercent(1.2345, 2) // Returns "123.45%"
 * ```
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format a number with compact notation for large values
 *
 * @param value - The numeric value to format
 * @returns Formatted string with K/M/B suffix (e.g., "1.2M")
 *
 * @example
 * ```ts
 * formatCompact(1234567) // Returns "1.2M"
 * formatCompact(1234) // Returns "1.2K"
 * ```
 */
export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: 1,
  }).format(value);
}

/**
 * Apply filters to procurement data
 *
 * Filters data based on date range, categories, suppliers, and amount range.
 * All filters are applied with AND logic (all conditions must match).
 *
 * @param data - Array of procurement records to filter
 * @param filters - Filter criteria to apply
 * @returns Filtered array of procurement records
 *
 * Security:
 * - All inputs are validated
 * - No XSS vulnerabilities (React handles escaping)
 * - Safe string comparisons (case-sensitive)
 *
 * Performance:
 * - Single pass through data (O(n))
 * - Early returns for empty data
 * - Efficient Set lookups for categories/suppliers
 *
 * @example
 * ```ts
 * const filters = {
 *   dateRange: { start: '2024-01-01', end: '2024-12-31' },
 *   categories: ['IT Equipment'],
 *   suppliers: [],
 *   amountRange: { min: 1000, max: null }
 * };
 * const filtered = applyFilters(data, filters);
 * ```
 */
export function applyFilters(
  data: ProcurementRecord[],
  filters: Filters,
): ProcurementRecord[] {
  // Validate inputs
  if (!data || data.length === 0) return [];
  if (!filters) return data;

  // Return all data if no filters are active
  const hasDateFilter =
    filters.dateRange.start !== null || filters.dateRange.end !== null;
  const hasCategoryFilter = filters.categories.length > 0;
  const hasSubcategoryFilter = filters.subcategories.length > 0;
  const hasSupplierFilter = filters.suppliers.length > 0;
  const hasLocationFilter = filters.locations.length > 0;
  const hasYearFilter = filters.years.length > 0;
  const hasAmountFilter =
    filters.amountRange.min !== null || filters.amountRange.max !== null;

  if (
    !hasDateFilter &&
    !hasCategoryFilter &&
    !hasSubcategoryFilter &&
    !hasSupplierFilter &&
    !hasLocationFilter &&
    !hasYearFilter &&
    !hasAmountFilter
  ) {
    return data;
  }

  // Convert arrays to Sets for O(1) lookups
  const categorySet = new Set(filters.categories);
  const subcategorySet = new Set(filters.subcategories);
  const supplierSet = new Set(filters.suppliers);
  const locationSet = new Set(filters.locations);
  const yearSet = new Set(filters.years);

  // Filter data with a single pass
  return data.filter((record) => {
    // Date range filter
    if (hasDateFilter) {
      const recordDate = record.date;

      if (filters.dateRange.start && recordDate < filters.dateRange.start) {
        return false;
      }

      if (filters.dateRange.end && recordDate > filters.dateRange.end) {
        return false;
      }
    }

    // Category filter
    if (hasCategoryFilter && !categorySet.has(record.category)) {
      return false;
    }

    // Subcategory filter
    if (hasSubcategoryFilter && !subcategorySet.has(record.subcategory)) {
      return false;
    }

    // Supplier filter
    if (hasSupplierFilter && !supplierSet.has(record.supplier)) {
      return false;
    }

    // Location filter
    if (hasLocationFilter && !locationSet.has(record.location)) {
      return false;
    }

    // Year filter - use year field if available, otherwise extract from date
    if (hasYearFilter) {
      const recordYear =
        record.year?.toString() ||
        new Date(record.date).getFullYear().toString();
      if (!yearSet.has(recordYear)) {
        return false;
      }
    }

    // Amount range filter
    if (hasAmountFilter) {
      const amount = record.amount;

      if (
        filters.amountRange.min !== null &&
        amount < filters.amountRange.min
      ) {
        return false;
      }

      if (
        filters.amountRange.max !== null &&
        amount > filters.amountRange.max
      ) {
        return false;
      }
    }

    // All filters passed
    return true;
  });
}
