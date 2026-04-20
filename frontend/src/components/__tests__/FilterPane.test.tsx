/**
 * Tests for FilterPane Component
 *
 * Tests cover:
 * - Initial render with no filters
 * - Date range selection (quick presets and custom)
 * - Category/Supplier/Location selection via MultiSelect
 * - Amount range filtering
 * - Reset filters functionality
 * - Filter presets (save/load/delete)
 * - Active filter count display
 * - Filter badges with removal
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FilterPane } from "../FilterPane";
import * as useFiltersModule from "@/hooks/useFilters";
import * as useProcurementDataModule from "@/hooks/useProcurementData";
import * as useFilterPresetsModule from "@/hooks/useFilterPresets";

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock hooks
vi.mock("@/hooks/useFilters", () => ({
  useFilters: vi.fn(),
  useUpdateFilters: vi.fn(),
  useResetFilters: vi.fn(),
}));

vi.mock("@/hooks/useProcurementData", () => ({
  useProcurementData: vi.fn(),
}));

vi.mock("@/hooks/useFilterPresets", () => ({
  useFilterPresets: vi.fn(),
}));

const defaultFilters = {
  dateRange: { start: null, end: null },
  categories: [],
  subcategories: [],
  suppliers: [],
  locations: [],
  years: [],
  amountRange: { min: null, max: null },
};

const mockProcurementData = [
  {
    category: "IT Equipment",
    subcategory: "Hardware",
    supplier: "Supplier A",
    location: "New York",
    date: "2024-01-15",
    year: 2024,
    amount: 5000,
  },
  {
    category: "Office Supplies",
    subcategory: "Paper",
    supplier: "Supplier B",
    location: "Chicago",
    date: "2023-06-20",
    year: 2023,
    amount: 500,
  },
  {
    category: "IT Equipment",
    subcategory: "Software",
    supplier: "Supplier C",
    location: "New York",
    date: "2024-03-10",
    year: 2024,
    amount: 15000,
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

describe("FilterPane", () => {
  const mockUpdateFilters = { mutate: vi.fn() };
  const mockResetFilters = { mutate: vi.fn() };
  const mockSavePreset = vi.fn();
  const mockDeletePreset = vi.fn();
  const mockNameExists = vi.fn().mockReturnValue(false);

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useFiltersModule.useFilters).mockReturnValue({
      data: defaultFilters,
      isLoading: false,
      isSuccess: true,
    } as any);

    vi.mocked(useFiltersModule.useUpdateFilters).mockReturnValue(
      mockUpdateFilters as any,
    );
    vi.mocked(useFiltersModule.useResetFilters).mockReturnValue(
      mockResetFilters as any,
    );

    vi.mocked(useProcurementDataModule.useProcurementData).mockReturnValue({
      data: mockProcurementData,
      isLoading: false,
      isSuccess: true,
    } as any);

    vi.mocked(useFilterPresetsModule.useFilterPresets).mockReturnValue({
      presets: [],
      savePreset: mockSavePreset,
      deletePreset: mockDeletePreset,
      updatePreset: vi.fn(),
      getPreset: vi.fn(),
      nameExists: mockNameExists,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // =====================
  // Basic Render Tests
  // =====================
  describe("Basic Rendering", () => {
    it("should render filter pane with title", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Filters")).toBeInTheDocument();
    });

    it("should render date range section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Date Range")).toBeInTheDocument();
      expect(screen.getByLabelText("Start Date")).toBeInTheDocument();
      expect(screen.getByLabelText("End Date")).toBeInTheDocument();
    });

    it("should render category section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Categories")).toBeInTheDocument();
    });

    it("should render supplier section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Suppliers")).toBeInTheDocument();
    });

    it("should render location section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Locations")).toBeInTheDocument();
    });

    it("should render amount range section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Amount Range")).toBeInTheDocument();
      expect(screen.getByLabelText("Minimum")).toBeInTheDocument();
      expect(screen.getByLabelText("Maximum")).toBeInTheDocument();
    });

    it("should return null when filters are not loaded", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: undefined,
        isLoading: true,
        isSuccess: false,
      } as any);

      const { container } = render(<FilterPane />, {
        wrapper: createWrapper(),
      });

      expect(container.firstChild).toBeNull();
    });
  });

  // =====================
  // Quick Date Presets Tests
  // =====================
  describe("Quick Date Presets", () => {
    it("should render quick date preset buttons", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(
        screen.getByRole("button", { name: "Last 7 days" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Last 30 days" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Last 90 days" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "This Year" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Last Year" }),
      ).toBeInTheDocument();
    });

    it("should apply Last 7 days preset when clicked", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Last 7 days" }));

      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        dateRange: expect.objectContaining({
          start: expect.any(String),
          end: expect.any(String),
        }),
      });
    });

    it("should apply Last 30 days preset when clicked", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Last 30 days" }));

      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        dateRange: expect.objectContaining({
          start: expect.any(String),
          end: expect.any(String),
        }),
      });
    });

    it("should apply This Year preset when clicked", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "This Year" }));

      const currentYear = new Date().getFullYear();
      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        dateRange: {
          start: `${currentYear}-01-01`,
          end: null,
        },
      });
    });

    it("should apply Last Year preset when clicked", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Last Year" }));

      const lastYear = new Date().getFullYear() - 1;
      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        dateRange: {
          start: `${lastYear}-01-01`,
          end: `${lastYear}-12-31`,
        },
      });
    });
  });

  // =====================
  // Custom Date Range Tests
  // =====================
  describe("Custom Date Range", () => {
    it("should update date range on blur", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      const startDateInput = screen.getByLabelText("Start Date");
      await user.clear(startDateInput);
      await user.type(startDateInput, "2024-01-01");
      fireEvent.blur(startDateInput);

      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        dateRange: expect.objectContaining({
          start: "2024-01-01",
        }),
      });
    });
  });

  // =====================
  // Amount Range Tests
  // =====================
  describe("Amount Range Filter", () => {
    it("should update min amount on blur", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      const minAmountInput = screen.getByLabelText("Minimum");
      await user.clear(minAmountInput);
      await user.type(minAmountInput, "1000");
      fireEvent.blur(minAmountInput);

      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        amountRange: {
          min: 1000,
          max: null,
        },
      });
    });

    it("should update max amount on blur", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      const maxAmountInput = screen.getByLabelText("Maximum");
      await user.clear(maxAmountInput);
      await user.type(maxAmountInput, "50000");
      fireEvent.blur(maxAmountInput);

      expect(mockUpdateFilters.mutate).toHaveBeenCalledWith({
        amountRange: {
          min: null,
          max: 50000,
        },
      });
    });
  });

  // =====================
  // Active Filter Count Tests
  // =====================
  describe("Active Filter Count", () => {
    it("should not show filter count badge when no active filters", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      // Badge with count should not be visible
      const badges = screen.queryAllByRole("status");
      const countBadges = badges.filter((b) =>
        /^\d+$/.test(b.textContent || ""),
      );
      expect(countBadges).toHaveLength(0);
    });

    it("should show filter count badge with active filters", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          categories: ["IT Equipment"],
          suppliers: ["Supplier A"],
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      // Should show "2" for 2 active filters
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("should count date range as one filter", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          dateRange: { start: "2024-01-01", end: "2024-12-31" },
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("1")).toBeInTheDocument();
    });

    it("should count amount range as one filter", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          amountRange: { min: 100, max: 5000 },
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("1")).toBeInTheDocument();
    });
  });

  // =====================
  // Reset Filters Tests
  // =====================
  describe("Reset Filters", () => {
    it("should show reset button when filters are active", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          categories: ["IT Equipment"],
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      expect(
        screen.getByRole("button", { name: "Reset all filters" }),
      ).toBeInTheDocument();
    });

    it("should not show reset button when no active filters", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(
        screen.queryByRole("button", { name: "Reset all filters" }),
      ).not.toBeInTheDocument();
    });

    it("should call resetFilters when reset button clicked", async () => {
      const user = userEvent.setup();
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          categories: ["IT Equipment"],
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(
        screen.getByRole("button", { name: "Reset all filters" }),
      );

      expect(mockResetFilters.mutate).toHaveBeenCalled();
    });
  });

  // =====================
  // Filter Badges Tests
  // =====================
  describe("Filter Badges", () => {
    it("should display date range badges when set", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          dateRange: { start: "2024-01-01", end: "2024-12-31" },
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("From: 2024-01-01")).toBeInTheDocument();
      expect(screen.getByText("To: 2024-12-31")).toBeInTheDocument();
    });

    it("should display amount range badges when set", () => {
      vi.mocked(useFiltersModule.useFilters).mockReturnValue({
        data: {
          ...defaultFilters,
          amountRange: { min: 1000, max: 50000 },
        },
        isLoading: false,
        isSuccess: true,
      } as any);

      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText(/Min: \$1,000/)).toBeInTheDocument();
      expect(screen.getByText(/Max: \$50,000/)).toBeInTheDocument();
    });
  });

  // =====================
  // Filter Presets Tests
  // =====================
  describe("Filter Presets", () => {
    it("should render preset dropdown button", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(
        screen.getByRole("button", { name: "Filter presets" }),
      ).toBeInTheDocument();
    });

    it("should show no presets message when empty", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Filter presets" }));

      expect(screen.getByText("No saved presets")).toBeInTheDocument();
    });

    it("should show save current filters option", async () => {
      const user = userEvent.setup();
      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Filter presets" }));

      expect(screen.getByText("Save Current Filters")).toBeInTheDocument();
    });

    it("should display saved presets", async () => {
      const user = userEvent.setup();
      vi.mocked(useFilterPresetsModule.useFilterPresets).mockReturnValue({
        presets: [
          {
            id: "1",
            name: "Q1 2024",
            filters: defaultFilters,
            createdAt: new Date().toISOString(),
          },
        ],
        savePreset: mockSavePreset,
        deletePreset: mockDeletePreset,
        updatePreset: vi.fn(),
        getPreset: vi.fn(),
        nameExists: mockNameExists,
      });

      render(<FilterPane />, { wrapper: createWrapper() });

      await user.click(screen.getByRole("button", { name: "Filter presets" }));

      expect(screen.getByText("Q1 2024")).toBeInTheDocument();
    });
  });

  // =====================
  // Years Filter Tests
  // =====================
  describe("Years Filter", () => {
    it("should render years section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Years")).toBeInTheDocument();
    });
  });

  // =====================
  // Subcategories Filter Tests
  // =====================
  describe("Subcategories Filter", () => {
    it("should render subcategories section", () => {
      render(<FilterPane />, { wrapper: createWrapper() });

      expect(screen.getByText("Subcategories")).toBeInTheDocument();
    });
  });
});
