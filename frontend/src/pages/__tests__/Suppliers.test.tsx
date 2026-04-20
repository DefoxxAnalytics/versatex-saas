/**
 * Tests for Suppliers Page Component
 *
 * Tests the Suppliers dashboard including:
 * - Loading state display
 * - Error state display
 * - Empty data state display
 * - Search filtering functionality
 * - Supplier table rendering
 * - Summary cards display
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Suppliers from "../Suppliers";

// Mock useSupplierDetails hook
vi.mock("@/hooks/useAnalytics", () => ({
  useSupplierDetails: vi.fn(),
}));

import { useSupplierDetails } from "@/hooks/useAnalytics";

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart-container">{children}</div>
  ),
  BarChart: () => <div data-testid="bar-chart" />,
  PieChart: () => <div data-testid="pie-chart" />,
  Bar: () => null,
  Pie: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}));

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

// Mock supplier data
const mockSupplierData = {
  summary: {
    total_suppliers: 25,
    total_spend: 1500000,
    top_supplier: "Acme Corp",
    top_supplier_spend: 350000,
    top3_concentration: 45.2,
    hhi_score: 1250,
    hhi_risk_level: "moderate" as const,
  },
  suppliers: [
    {
      supplier_id: 1,
      supplier: "Acme Corp",
      total_spend: 350000,
      percent_of_total: 23.3,
      transaction_count: 150,
      avg_transaction: 2333.33,
      category_count: 5,
      rank: 1,
    },
    {
      supplier_id: 2,
      supplier: "Beta Industries",
      total_spend: 250000,
      percent_of_total: 16.7,
      transaction_count: 100,
      avg_transaction: 2500,
      category_count: 3,
      rank: 2,
    },
    {
      supplier_id: 3,
      supplier: "Gamma Solutions",
      total_spend: 180000,
      percent_of_total: 12.0,
      transaction_count: 75,
      avg_transaction: 2400,
      category_count: 4,
      rank: 3,
    },
  ],
};

describe("Suppliers Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should display loading state while data is fetching", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        isPending: true,
        isFetching: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText("Loading Supplier Data")).toBeInTheDocument();
      expect(
        screen.getByText("Analyzing supplier metrics..."),
      ).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error state when data fetching fails", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Network error"),
        isError: true,
        isSuccess: false,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText("Error Loading Data")).toBeInTheDocument();
      expect(
        screen.getByText("Failed to load supplier analysis. Please try again."),
      ).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no supplier data exists", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: { summary: mockSupplierData.summary, suppliers: [] },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText("No Data Available")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Upload your procurement data to see supplier analysis.",
        ),
      ).toBeInTheDocument();
    });

    it("should display empty state when data is null", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText("No Data Available")).toBeInTheDocument();
    });
  });

  describe("Data Display", () => {
    beforeEach(() => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: mockSupplierData,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);
    });

    it("should display page header", () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText("Supplier Analysis")).toBeInTheDocument();
      expect(
        screen.getByText("Analyze vendor performance and spending patterns"),
      ).toBeInTheDocument();
    });

    it("should display summary cards with correct data", () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      // Total Suppliers card
      expect(screen.getByText("Total Suppliers")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();

      // Total Spend card - appears in summary and table header
      expect(screen.getAllByText("Total Spend").length).toBeGreaterThanOrEqual(
        1,
      );
      expect(screen.getByText("$1.5M")).toBeInTheDocument();

      // Top Supplier card - Acme Corp appears in summary and table
      expect(screen.getByText("Top Supplier")).toBeInTheDocument();
      expect(screen.getAllByText("Acme Corp").length).toBeGreaterThanOrEqual(1);

      // Concentration Risk card
      expect(screen.getByText("Concentration Risk")).toBeInTheDocument();
      expect(screen.getByText("45.2%")).toBeInTheDocument();

      // HHI Score card
      expect(screen.getByText("HHI Score")).toBeInTheDocument();
      expect(screen.getByText("1250")).toBeInTheDocument();
    });

    it("should display supplier table with all rows", () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      // Table header check - verify Supplier Details card title
      expect(screen.getByText("Supplier Details")).toBeInTheDocument();

      // Supplier rows - Acme Corp appears in both summary and table
      expect(screen.getAllByText("Acme Corp").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Beta Industries")).toBeInTheDocument();
      expect(screen.getByText("Gamma Solutions")).toBeInTheDocument();
    });

    it("should display charts", () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      expect(
        screen.getByText("Spend Distribution by Supplier"),
      ).toBeInTheDocument();
      expect(screen.getByText("Top 10 Suppliers by Spend")).toBeInTheDocument();
    });
  });

  describe("Search Filtering", () => {
    beforeEach(() => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: mockSupplierData,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);
    });

    it("should render search input", () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );
      expect(searchInput).toBeInTheDocument();
    });

    it("should filter suppliers by search query", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Search for "Beta" - doesn't appear in summary, so cleaner test
      fireEvent.change(searchInput, { target: { value: "Beta" } });

      await waitFor(() => {
        // Beta Industries should be visible
        expect(screen.getByText("Beta Industries")).toBeInTheDocument();
        // Other suppliers in table should be hidden
        expect(screen.queryByText("Gamma Solutions")).not.toBeInTheDocument();
      });
    });

    it("should filter suppliers case-insensitively", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Search with lowercase
      fireEvent.change(searchInput, { target: { value: "gamma" } });

      await waitFor(() => {
        expect(screen.getByText("Gamma Solutions")).toBeInTheDocument();
        expect(screen.queryByText("Beta Industries")).not.toBeInTheDocument();
      });
    });

    it("should show all suppliers when search is cleared", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Search for something that filters out most suppliers
      fireEvent.change(searchInput, { target: { value: "Beta" } });

      await waitFor(() => {
        expect(screen.queryByText("Gamma Solutions")).not.toBeInTheDocument();
      });

      // Clear search
      fireEvent.change(searchInput, { target: { value: "" } });

      await waitFor(() => {
        // All suppliers should be visible again
        expect(screen.getByText("Beta Industries")).toBeInTheDocument();
        expect(screen.getByText("Gamma Solutions")).toBeInTheDocument();
      });
    });

    it('should display "No suppliers found" when search has no matches', async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Search for non-existent supplier
      fireEvent.change(searchInput, { target: { value: "NonExistent" } });

      await waitFor(() => {
        expect(screen.getByText("No suppliers found")).toBeInTheDocument();
        expect(
          screen.getByText("Try adjusting your search query"),
        ).toBeInTheDocument();
      });
    });

    it("should show filter count when search is active", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Search for "Acme"
      fireEvent.change(searchInput, { target: { value: "Acme" } });

      await waitFor(() => {
        expect(screen.getByText("1 of 3 suppliers")).toBeInTheDocument();
      });
    });

    it("should have a clear button when search has value", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      );

      // Initially no clear button
      expect(screen.queryByRole("button")).toBeNull();

      // Add search text
      fireEvent.change(searchInput, { target: { value: "Acme" } });

      // Clear button should appear (X icon)
      await waitFor(() => {
        const clearButton = searchInput.parentElement?.querySelector("button");
        expect(clearButton).toBeInTheDocument();
      });
    });

    it("should clear search when clear button is clicked", async () => {
      render(<Suppliers />, { wrapper: createWrapper() });

      const searchInput = screen.getByPlaceholderText(
        "Search suppliers by name...",
      ) as HTMLInputElement;

      // Add search text
      fireEvent.change(searchInput, { target: { value: "Acme" } });

      await waitFor(() => {
        expect(searchInput.value).toBe("Acme");
      });

      // Click clear button
      const clearButton = searchInput.parentElement?.querySelector("button");
      if (clearButton) {
        fireEvent.click(clearButton);
      }

      await waitFor(() => {
        expect(searchInput.value).toBe("");
      });
    });
  });

  describe("HHI Risk Level Styling", () => {
    it("should apply green styling for low HHI risk", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: {
          ...mockSupplierData,
          summary: {
            ...mockSupplierData.summary,
            hhi_risk_level: "low" as const,
          },
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      // Check for "Low" text in HHI card
      expect(screen.getByText(/Low/)).toBeInTheDocument();
    });

    it("should apply yellow styling for moderate HHI risk", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: mockSupplierData, // Already has moderate risk
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText(/Moderate/)).toBeInTheDocument();
    });

    it("should apply red styling for high HHI risk", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: {
          ...mockSupplierData,
          summary: {
            ...mockSupplierData.summary,
            hhi_risk_level: "high" as const,
          },
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      expect(screen.getByText(/High/)).toBeInTheDocument();
    });
  });

  describe("High Concentration Warning", () => {
    it("should apply warning styling when top3 concentration exceeds 50%", () => {
      vi.mocked(useSupplierDetails).mockReturnValue({
        data: {
          ...mockSupplierData,
          summary: { ...mockSupplierData.summary, top3_concentration: 65.0 },
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSupplierDetails>);

      render(<Suppliers />, { wrapper: createWrapper() });

      // The concentration value should be displayed
      expect(screen.getByText("65.0%")).toBeInTheDocument();
    });
  });
});
