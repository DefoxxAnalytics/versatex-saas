import { describe, it, expect } from "vitest";
import {
  applyFilters,
  formatCurrency,
  formatPercent,
  formatCompact,
} from "../analytics";
import type { ProcurementRecord } from "../../hooks/useProcurementData";
import type { Filters } from "../../hooks/useFilters";

/**
 * Helper to create a full Filters object with default empty values
 */
function createFilters(partial: Partial<Filters> = {}): Filters {
  return {
    dateRange: { start: null, end: null },
    categories: [],
    subcategories: [],
    suppliers: [],
    locations: [],
    years: [],
    amountRange: { min: null, max: null },
    ...partial,
  };
}

/**
 * Test suite for applyFilters utility
 *
 * Note: Other analytics calculations (totals, averages, aggregations)
 * are now handled by backend APIs and tested via API integration tests.
 */

const mockData: ProcurementRecord[] = [
  {
    date: "2024-01-15",
    supplier: "Acme Corp",
    category: "Office Supplies",
    subcategory: "Writing",
    location: "New York",
    year: 2024,
    amount: 1500,
    description: "Pens and paper",
  },
  {
    date: "2024-01-20",
    supplier: "Tech Solutions",
    category: "IT Equipment",
    subcategory: "Hardware",
    location: "Chicago",
    year: 2024,
    amount: 5000,
    description: "Laptops",
  },
  {
    date: "2024-02-10",
    supplier: "Acme Corp",
    category: "Office Supplies",
    subcategory: "Desktop",
    location: "New York",
    year: 2024,
    amount: 800,
    description: "Staplers",
  },
  {
    date: "2024-02-15",
    supplier: "Office Depot",
    category: "Office Supplies",
    subcategory: "Furniture",
    location: "Boston",
    year: 2024,
    amount: 1200,
    description: "Chairs",
  },
  {
    date: "2023-03-01",
    supplier: "Tech Solutions",
    category: "IT Equipment",
    subcategory: "Hardware",
    location: "Chicago",
    year: 2023,
    amount: 3000,
    description: "Monitors",
  },
];

describe("applyFilters", () => {
  describe("Date Range Filtering", () => {
    it("should filter by start date only", () => {
      const filters = createFilters({
        dateRange: { start: "2024-02-01", end: null },
      });

      const filtered = applyFilters(mockData, filters);

      // Should include records from Feb 10, Feb 15 (2024 records after Feb 1)
      // 2023-03-01 record is before 2024-02-01 so excluded
      expect(filtered.length).toBe(2);
      expect(filtered.every((r) => r.date >= "2024-02-01")).toBe(true);
    });

    it("should filter by end date only", () => {
      const filters = createFilters({
        dateRange: { start: null, end: "2024-02-01" },
      });

      const filtered = applyFilters(mockData, filters);

      // Should include records from Jan 15, Jan 20, and 2023-03-01 (all <= 2024-02-01)
      expect(filtered.length).toBe(3);
      expect(filtered.every((r) => r.date <= "2024-02-01")).toBe(true);
    });

    it("should filter by date range", () => {
      const filters = createFilters({
        dateRange: { start: "2024-02-01", end: "2024-02-28" },
      });

      const filtered = applyFilters(mockData, filters);

      // Should include only Feb records
      expect(filtered.length).toBe(2);
      expect(
        filtered.every((r) => r.date >= "2024-02-01" && r.date <= "2024-02-28"),
      ).toBe(true);
    });
  });

  describe("Category Filtering", () => {
    it("should filter by single category", () => {
      const filters = createFilters({
        categories: ["IT Equipment"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.category === "IT Equipment")).toBe(true);
      expect(filtered.length).toBe(2);
    });

    it("should filter by multiple categories", () => {
      const filters = createFilters({
        categories: ["IT Equipment", "Office Supplies"],
      });

      const filtered = applyFilters(mockData, filters);

      // All records match these categories
      expect(filtered.length).toBe(mockData.length);
    });

    it("should return empty array for non-matching category", () => {
      const filters = createFilters({
        categories: ["Non-existent Category"],
      });

      const filtered = applyFilters(mockData, filters);
      expect(filtered.length).toBe(0);
    });
  });

  describe("Supplier Filtering", () => {
    it("should filter by single supplier", () => {
      const filters = createFilters({
        suppliers: ["Acme Corp"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.supplier === "Acme Corp")).toBe(true);
      expect(filtered.length).toBe(2);
    });

    it("should filter by multiple suppliers", () => {
      const filters = createFilters({
        suppliers: ["Acme Corp", "Tech Solutions"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(
        filtered.every(
          (r) => r.supplier === "Acme Corp" || r.supplier === "Tech Solutions",
        ),
      ).toBe(true);
      expect(filtered.length).toBe(4);
    });
  });

  describe("Subcategory Filtering", () => {
    it("should filter by single subcategory", () => {
      const filters = createFilters({
        subcategories: ["Hardware"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.subcategory === "Hardware")).toBe(true);
      expect(filtered.length).toBe(2);
    });

    it("should filter by multiple subcategories", () => {
      const filters = createFilters({
        subcategories: ["Hardware", "Writing"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.length).toBe(3);
    });
  });

  describe("Location Filtering", () => {
    it("should filter by single location", () => {
      const filters = createFilters({
        locations: ["New York"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.location === "New York")).toBe(true);
      expect(filtered.length).toBe(2);
    });

    it("should filter by multiple locations", () => {
      const filters = createFilters({
        locations: ["New York", "Chicago"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.length).toBe(4);
    });
  });

  describe("Year Filtering", () => {
    it("should filter by single year", () => {
      const filters = createFilters({
        years: ["2024"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.year === 2024)).toBe(true);
      expect(filtered.length).toBe(4);
    });

    it("should filter by multiple years", () => {
      const filters = createFilters({
        years: ["2023", "2024"],
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.length).toBe(5);
    });
  });

  describe("Amount Range Filtering", () => {
    it("should filter by minimum amount only", () => {
      const filters = createFilters({
        amountRange: { min: 2000, max: null },
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.amount >= 2000)).toBe(true);
      expect(filtered.length).toBe(2); // 5000 and 3000
    });

    it("should filter by maximum amount only", () => {
      const filters = createFilters({
        amountRange: { min: null, max: 1500 },
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.amount <= 1500)).toBe(true);
      expect(filtered.length).toBe(3); // 1500, 800, 1200
    });

    it("should filter by amount range", () => {
      const filters = createFilters({
        amountRange: { min: 1000, max: 2000 },
      });

      const filtered = applyFilters(mockData, filters);

      expect(filtered.every((r) => r.amount >= 1000 && r.amount <= 2000)).toBe(
        true,
      );
      expect(filtered.length).toBe(2); // 1500, 1200
    });
  });

  describe("Combined Filters", () => {
    it("should apply multiple filters together", () => {
      const filters = createFilters({
        dateRange: { start: "2024-01-01", end: "2024-02-28" },
        categories: ["Office Supplies"],
        suppliers: ["Acme Corp"],
        amountRange: { min: 500, max: 2000 },
      });

      const filtered = applyFilters(mockData, filters);

      // Should match: Acme Corp, Office Supplies, Jan-Feb, 500-2000
      expect(filtered.length).toBe(2); // Jan 15 (1500) and Feb 10 (800)
      expect(
        filtered.every(
          (r) =>
            r.supplier === "Acme Corp" &&
            r.category === "Office Supplies" &&
            r.date >= "2024-01-01" &&
            r.date <= "2024-02-28" &&
            r.amount >= 500 &&
            r.amount <= 2000,
        ),
      ).toBe(true);
    });

    it("should return all data when no filters applied", () => {
      const filters = createFilters();

      const filtered = applyFilters(mockData, filters);
      expect(filtered.length).toBe(mockData.length);
    });

    it("should handle empty data array", () => {
      const filters = createFilters({
        dateRange: { start: "2024-01-01", end: "2024-12-31" },
        categories: ["Office Supplies"],
      });

      const filtered = applyFilters([], filters);
      expect(filtered.length).toBe(0);
    });
  });

  describe("Edge Cases", () => {
    it("should handle invalid date formats gracefully", () => {
      const filters = createFilters({
        dateRange: { start: "invalid-date", end: null },
      });

      // Should not crash, return all data or empty based on implementation
      const filtered = applyFilters(mockData, filters);
      expect(Array.isArray(filtered)).toBe(true);
    });

    it("should handle negative amounts in filter", () => {
      const filters = createFilters({
        amountRange: { min: -1000, max: 1000 },
      });

      const filtered = applyFilters(mockData, filters);
      expect(filtered.every((r) => r.amount >= -1000 && r.amount <= 1000)).toBe(
        true,
      );
    });

    it("should be case-sensitive for category and supplier names", () => {
      const filters = createFilters({
        categories: ["office supplies"], // lowercase
      });

      const filtered = applyFilters(mockData, filters);
      // Should not match 'Office Supplies' (capital O and S)
      expect(filtered.length).toBe(0);
    });
  });
});

// =====================
// Format Functions Tests
// =====================
describe("formatCurrency", () => {
  it("should format positive numbers as USD currency", () => {
    expect(formatCurrency(1234567)).toBe("$1,234,567");
  });

  it("should format small numbers", () => {
    expect(formatCurrency(100)).toBe("$100");
  });

  it("should format zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });

  it("should round decimals", () => {
    expect(formatCurrency(1234.56)).toBe("$1,235");
  });

  it("should handle negative numbers", () => {
    expect(formatCurrency(-500)).toBe("-$500");
  });

  it("should handle very large numbers", () => {
    expect(formatCurrency(1000000000)).toBe("$1,000,000,000");
  });
});

describe("formatPercent", () => {
  it("should format decimal as percentage", () => {
    expect(formatPercent(0.756)).toBe("75.6%");
  });

  it("should use default 1 decimal place", () => {
    expect(formatPercent(0.5)).toBe("50.0%");
  });

  it("should support custom decimal places", () => {
    expect(formatPercent(0.12345, 2)).toBe("12.35%");
  });

  it("should handle zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });

  it("should handle values over 100%", () => {
    expect(formatPercent(1.5)).toBe("150.0%");
  });

  it("should handle negative percentages", () => {
    expect(formatPercent(-0.25)).toBe("-25.0%");
  });
});

describe("formatCompact", () => {
  it("should format thousands with K suffix", () => {
    expect(formatCompact(1234)).toBe("1.2K");
  });

  it("should format millions with M suffix", () => {
    expect(formatCompact(1234567)).toBe("1.2M");
  });

  it("should format billions with B suffix", () => {
    expect(formatCompact(1234567890)).toBe("1.2B");
  });

  it("should handle small numbers without suffix", () => {
    expect(formatCompact(123)).toBe("123");
  });

  it("should handle zero", () => {
    expect(formatCompact(0)).toBe("0");
  });
});
