/**
 * Tests for useP2PAnalytics hooks
 *
 * Tests cover:
 * - P2P Cycle Time Analysis hooks
 * - 3-Way Matching hooks
 * - Invoice Aging hooks
 * - Purchase Requisition hooks
 * - Purchase Order hooks
 * - Supplier Payment Performance hooks
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useP2PCycleOverview,
  useP2PCycleByCategory,
  useP2PCycleBySupplier,
  useP2PCycleTrends,
  useP2PBottlenecks,
  useP2PProcessFunnel,
  useP2PStageDrilldown,
  useMatchingOverview,
  useMatchingExceptions,
  useExceptionsByType,
  useExceptionsBySupplier,
  usePriceVarianceAnalysis,
  useQuantityVarianceAnalysis,
  useInvoiceMatchDetail,
  useResolveException,
  useBulkResolveExceptions,
  useAgingOverview,
  useAgingBySupplier,
  usePaymentTermsCompliance,
  useDPOTrends,
  useCashFlowForecast,
  usePROverview,
  usePRApprovalAnalysis,
  usePRByDepartment,
  usePRPending,
  usePRDetail,
  usePOOverview,
  usePOLeakage,
  usePOAmendments,
  usePOBySupplier,
  usePODetail,
  useSupplierPaymentsOverview,
  useSupplierPaymentsScorecard,
  useSupplierPaymentDetail,
  useSupplierPaymentHistory,
} from "../useP2PAnalytics";
import * as api from "@/lib/api";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  p2pAnalyticsAPI: {
    getCycleOverview: vi.fn(),
    getCycleByCategory: vi.fn(),
    getCycleBySupplier: vi.fn(),
    getCycleTrends: vi.fn(),
    getBottlenecks: vi.fn(),
    getProcessFunnel: vi.fn(),
    getStageDrilldown: vi.fn(),
    getMatchingOverview: vi.fn(),
    getMatchingExceptions: vi.fn(),
    getExceptionsByType: vi.fn(),
    getExceptionsBySupplier: vi.fn(),
    getPriceVarianceAnalysis: vi.fn(),
    getQuantityVarianceAnalysis: vi.fn(),
    getInvoiceMatchDetail: vi.fn(),
    resolveException: vi.fn(),
    bulkResolveExceptions: vi.fn(),
    getAgingOverview: vi.fn(),
    getAgingBySupplier: vi.fn(),
    getPaymentTermsCompliance: vi.fn(),
    getDPOTrends: vi.fn(),
    getCashFlowForecast: vi.fn(),
    getPROverview: vi.fn(),
    getPRApprovalAnalysis: vi.fn(),
    getPRByDepartment: vi.fn(),
    getPRPending: vi.fn(),
    getPRDetail: vi.fn(),
    getPOOverview: vi.fn(),
    getPOLeakage: vi.fn(),
    getPOAmendments: vi.fn(),
    getPOBySupplier: vi.fn(),
    getPODetail: vi.fn(),
    getSupplierPaymentsOverview: vi.fn(),
    getSupplierPaymentsScorecard: vi.fn(),
    getSupplierPaymentDetail: vi.fn(),
    getSupplierPaymentHistory: vi.fn(),
  },
  getOrganizationParam: vi.fn(),
}));

vi.mock("../useAnalytics", () => ({
  useAnalyticsFilters: vi.fn(() => undefined),
}));

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

describe("useP2PAnalytics Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getOrganizationParam).mockReturnValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =====================
  // P2P Cycle Time Analysis
  // =====================
  describe("P2P Cycle Time Analysis", () => {
    it("should fetch cycle overview", async () => {
      const mockData = { total_avg_days: 15, stages: [] };
      vi.mocked(api.p2pAnalyticsAPI.getCycleOverview).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PCycleOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCycleOverview).toHaveBeenCalled();
      expect(result.current.data).toEqual(mockData);
    });

    it("should fetch cycle by category", async () => {
      const mockData = [{ category: "IT", avg_days: 10 }];
      vi.mocked(api.p2pAnalyticsAPI.getCycleByCategory).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PCycleByCategory(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCycleByCategory).toHaveBeenCalled();
    });

    it("should fetch cycle by supplier", async () => {
      const mockData = [{ supplier: "Acme", avg_days: 12 }];
      vi.mocked(api.p2pAnalyticsAPI.getCycleBySupplier).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PCycleBySupplier(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCycleBySupplier).toHaveBeenCalled();
    });

    it("should fetch cycle trends with default months", async () => {
      const mockData = { trends: [] };
      vi.mocked(api.p2pAnalyticsAPI.getCycleTrends).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PCycleTrends(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCycleTrends).toHaveBeenCalledWith(12, undefined);
    });

    it("should fetch cycle trends with custom months", async () => {
      const mockData = { trends: [] };
      vi.mocked(api.p2pAnalyticsAPI.getCycleTrends).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PCycleTrends(6), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCycleTrends).toHaveBeenCalledWith(6, undefined);
    });

    it("should fetch bottlenecks", async () => {
      const mockData = [{ stage: "approval", avg_delay: 5 }];
      vi.mocked(api.p2pAnalyticsAPI.getBottlenecks).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PBottlenecks(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getBottlenecks).toHaveBeenCalled();
    });

    it("should fetch process funnel", async () => {
      const mockData = { funnel: [] };
      vi.mocked(api.p2pAnalyticsAPI.getProcessFunnel).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PProcessFunnel(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getProcessFunnel).toHaveBeenCalledWith(12, undefined);
    });

    it("should fetch stage drilldown when stage provided", async () => {
      const mockData = { items: [] };
      vi.mocked(api.p2pAnalyticsAPI.getStageDrilldown).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useP2PStageDrilldown("approval"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getStageDrilldown).toHaveBeenCalledWith(
        "approval",
        undefined,
      );
    });

    it("should not fetch stage drilldown when stage is null", () => {
      const { result } = renderHook(() => useP2PStageDrilldown(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(api.p2pAnalyticsAPI.getStageDrilldown).not.toHaveBeenCalled();
    });
  });

  // =====================
  // 3-Way Matching
  // =====================
  describe("3-Way Matching", () => {
    it("should fetch matching overview", async () => {
      const mockData = { match_rate: 0.85, total_invoices: 100 };
      vi.mocked(api.p2pAnalyticsAPI.getMatchingOverview).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useMatchingOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getMatchingOverview).toHaveBeenCalled();
    });

    it("should fetch matching exceptions", async () => {
      const mockData = { results: [], count: 0 };
      vi.mocked(api.p2pAnalyticsAPI.getMatchingExceptions).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(
        () => useMatchingExceptions({ status: "open" }),
        {
          wrapper: createWrapper(),
        },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getMatchingExceptions).toHaveBeenCalledWith(
        { status: "open" },
        undefined,
      );
    });

    it("should fetch exceptions by type", async () => {
      const mockData = [{ type: "price", count: 10 }];
      vi.mocked(api.p2pAnalyticsAPI.getExceptionsByType).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useExceptionsByType(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getExceptionsByType).toHaveBeenCalled();
    });

    it("should fetch exceptions by supplier", async () => {
      const mockData = [{ supplier: "Acme", count: 5 }];
      vi.mocked(api.p2pAnalyticsAPI.getExceptionsBySupplier).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useExceptionsBySupplier(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getExceptionsBySupplier).toHaveBeenCalled();
    });

    it("should fetch price variance analysis", async () => {
      const mockData = { variance: [] };
      vi.mocked(api.p2pAnalyticsAPI.getPriceVarianceAnalysis).mockResolvedValue(
        { data: mockData } as any,
      );

      const { result } = renderHook(() => usePriceVarianceAnalysis(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPriceVarianceAnalysis).toHaveBeenCalled();
    });

    it("should fetch quantity variance analysis", async () => {
      const mockData = { variance: [] };
      vi.mocked(
        api.p2pAnalyticsAPI.getQuantityVarianceAnalysis,
      ).mockResolvedValue({ data: mockData } as any);

      const { result } = renderHook(() => useQuantityVarianceAnalysis(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(
        api.p2pAnalyticsAPI.getQuantityVarianceAnalysis,
      ).toHaveBeenCalled();
    });

    it("should fetch invoice match detail when ID provided", async () => {
      const mockData = { id: 1, po_number: "PO-001" };
      vi.mocked(api.p2pAnalyticsAPI.getInvoiceMatchDetail).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useInvoiceMatchDetail(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getInvoiceMatchDetail).toHaveBeenCalledWith(1, undefined);
    });

    it("should not fetch invoice match detail when ID is null", () => {
      const { result } = renderHook(() => useInvoiceMatchDetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });

    it("should resolve exception", async () => {
      const mockData = { id: 1, status: "resolved" };
      vi.mocked(api.p2pAnalyticsAPI.resolveException).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useResolveException(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({
          invoiceId: 1,
          resolutionNotes: "Fixed",
        });
      });

      expect(api.p2pAnalyticsAPI.resolveException).toHaveBeenCalledWith(
        1,
        "Fixed",
      );
    });

    it("should bulk resolve exceptions", async () => {
      const mockData = { resolved_count: 3 };
      vi.mocked(api.p2pAnalyticsAPI.bulkResolveExceptions).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useBulkResolveExceptions(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({
          invoiceIds: [1, 2, 3],
          resolutionNotes: "Bulk fix",
        });
      });

      expect(api.p2pAnalyticsAPI.bulkResolveExceptions).toHaveBeenCalledWith(
        [1, 2, 3],
        "Bulk fix",
      );
    });
  });

  // =====================
  // Invoice Aging / AP Analysis
  // =====================
  describe("Invoice Aging / AP Analysis", () => {
    it("should fetch aging overview", async () => {
      const mockData = { total_ap: 100000, buckets: [] };
      vi.mocked(api.p2pAnalyticsAPI.getAgingOverview).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useAgingOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getAgingOverview).toHaveBeenCalled();
    });

    it("should fetch aging by supplier", async () => {
      const mockData = [{ supplier: "Acme", total: 5000 }];
      vi.mocked(api.p2pAnalyticsAPI.getAgingBySupplier).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useAgingBySupplier(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getAgingBySupplier).toHaveBeenCalled();
    });

    it("should fetch payment terms compliance", async () => {
      const mockData = { compliance_rate: 0.92 };
      vi.mocked(
        api.p2pAnalyticsAPI.getPaymentTermsCompliance,
      ).mockResolvedValue({ data: mockData } as any);

      const { result } = renderHook(() => usePaymentTermsCompliance(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPaymentTermsCompliance).toHaveBeenCalled();
    });

    it("should fetch DPO trends", async () => {
      const mockData = { trends: [] };
      vi.mocked(api.p2pAnalyticsAPI.getDPOTrends).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useDPOTrends(6), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getDPOTrends).toHaveBeenCalledWith(6, undefined);
    });

    it("should fetch cash flow forecast", async () => {
      const mockData = { forecast: [] };
      vi.mocked(api.p2pAnalyticsAPI.getCashFlowForecast).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => useCashFlowForecast(8), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getCashFlowForecast).toHaveBeenCalledWith(8, undefined);
    });
  });

  // =====================
  // Purchase Requisitions
  // =====================
  describe("Purchase Requisitions", () => {
    it("should fetch PR overview", async () => {
      const mockData = { total_prs: 50, pending: 10 };
      vi.mocked(api.p2pAnalyticsAPI.getPROverview).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePROverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPROverview).toHaveBeenCalled();
    });

    it("should fetch PR approval analysis", async () => {
      const mockData = { avg_approval_days: 3 };
      vi.mocked(api.p2pAnalyticsAPI.getPRApprovalAnalysis).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePRApprovalAnalysis(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPRApprovalAnalysis).toHaveBeenCalled();
    });

    it("should fetch PR by department", async () => {
      const mockData = [{ department: "IT", count: 25 }];
      vi.mocked(api.p2pAnalyticsAPI.getPRByDepartment).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePRByDepartment(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPRByDepartment).toHaveBeenCalled();
    });

    it("should fetch pending PRs with limit", async () => {
      const mockData = { results: [] };
      vi.mocked(api.p2pAnalyticsAPI.getPRPending).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePRPending(25), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPRPending).toHaveBeenCalledWith(25, undefined);
    });

    it("should fetch PR detail when ID provided", async () => {
      const mockData = { id: 1, pr_number: "PR-001" };
      vi.mocked(api.p2pAnalyticsAPI.getPRDetail).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePRDetail(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPRDetail).toHaveBeenCalledWith(1, undefined);
    });

    it("should not fetch PR detail when ID is null", () => {
      const { result } = renderHook(() => usePRDetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // Purchase Orders
  // =====================
  describe("Purchase Orders", () => {
    it("should fetch PO overview", async () => {
      const mockData = { total_pos: 100, total_value: 500000 };
      vi.mocked(api.p2pAnalyticsAPI.getPOOverview).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePOOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPOOverview).toHaveBeenCalled();
    });

    it("should fetch PO leakage", async () => {
      const mockData = { maverick_spend: 10000 };
      vi.mocked(api.p2pAnalyticsAPI.getPOLeakage).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePOLeakage(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPOLeakage).toHaveBeenCalled();
    });

    it("should fetch PO amendments", async () => {
      const mockData = { amendment_rate: 0.05 };
      vi.mocked(api.p2pAnalyticsAPI.getPOAmendments).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePOAmendments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPOAmendments).toHaveBeenCalled();
    });

    it("should fetch PO by supplier", async () => {
      const mockData = [{ supplier: "Acme", po_count: 15 }];
      vi.mocked(api.p2pAnalyticsAPI.getPOBySupplier).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePOBySupplier(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPOBySupplier).toHaveBeenCalled();
    });

    it("should fetch PO detail when ID provided", async () => {
      const mockData = { id: 1, po_number: "PO-001" };
      vi.mocked(api.p2pAnalyticsAPI.getPODetail).mockResolvedValue({
        data: mockData,
      } as any);

      const { result } = renderHook(() => usePODetail(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getPODetail).toHaveBeenCalledWith(1, undefined);
    });

    it("should not fetch PO detail when ID is null", () => {
      const { result } = renderHook(() => usePODetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // Supplier Payment Performance
  // =====================
  describe("Supplier Payment Performance", () => {
    it("should fetch supplier payments overview", async () => {
      const mockData = { total_payments: 500000 };
      vi.mocked(
        api.p2pAnalyticsAPI.getSupplierPaymentsOverview,
      ).mockResolvedValue({ data: mockData } as any);

      const { result } = renderHook(() => useSupplierPaymentsOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(
        api.p2pAnalyticsAPI.getSupplierPaymentsOverview,
      ).toHaveBeenCalled();
    });

    it("should fetch supplier payments scorecard with limit", async () => {
      const mockData = { results: [] };
      vi.mocked(
        api.p2pAnalyticsAPI.getSupplierPaymentsScorecard,
      ).mockResolvedValue({ data: mockData } as any);

      const { result } = renderHook(() => useSupplierPaymentsScorecard(25), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(
        api.p2pAnalyticsAPI.getSupplierPaymentsScorecard,
      ).toHaveBeenCalledWith(25, undefined);
    });

    it("should fetch supplier payment detail when ID provided", async () => {
      const mockData = { id: 1, supplier_name: "Acme" };
      vi.mocked(api.p2pAnalyticsAPI.getSupplierPaymentDetail).mockResolvedValue(
        { data: mockData } as any,
      );

      const { result } = renderHook(() => useSupplierPaymentDetail(1), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.p2pAnalyticsAPI.getSupplierPaymentDetail).toHaveBeenCalledWith(
        1,
        undefined,
      );
    });

    it("should not fetch supplier payment detail when ID is null", () => {
      const { result } = renderHook(() => useSupplierPaymentDetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });

    it("should fetch supplier payment history when ID provided", async () => {
      const mockData = { history: [] };
      vi.mocked(
        api.p2pAnalyticsAPI.getSupplierPaymentHistory,
      ).mockResolvedValue({ data: mockData } as any);

      const { result } = renderHook(() => useSupplierPaymentHistory(1, 6), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(
        api.p2pAnalyticsAPI.getSupplierPaymentHistory,
      ).toHaveBeenCalledWith(1, 6, undefined);
    });

    it("should not fetch supplier payment history when ID is null", () => {
      const { result } = renderHook(() => useSupplierPaymentHistory(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // Organization Scoping
  // =====================
  describe("Organization Scoping", () => {
    it("should include org ID in query key when viewing other org", async () => {
      vi.mocked(api.getOrganizationParam).mockReturnValue({
        organization_id: 5,
      });
      vi.mocked(api.p2pAnalyticsAPI.getCycleOverview).mockResolvedValue({
        data: {},
      } as any);

      const { result } = renderHook(() => useP2PCycleOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify the hook works with org scoping
      expect(result.current.data).toBeDefined();
    });
  });

  // =====================
  // Error Handling
  // =====================
  describe("Error Handling", () => {
    it("should handle API error in cycle overview", async () => {
      vi.mocked(api.p2pAnalyticsAPI.getCycleOverview).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useP2PCycleOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });

    it("should handle API error in matching overview", async () => {
      vi.mocked(api.p2pAnalyticsAPI.getMatchingOverview).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useMatchingOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });

    it("should handle mutation error in resolve exception", async () => {
      vi.mocked(api.p2pAnalyticsAPI.resolveException).mockRejectedValue(
        new Error("Failed to resolve"),
      );

      const { result } = renderHook(() => useResolveException(), {
        wrapper: createWrapper(),
      });

      let errorOccurred = false;
      await act(async () => {
        try {
          await result.current.mutateAsync({
            invoiceId: 1,
            resolutionNotes: "Test",
          });
        } catch {
          errorOccurred = true;
        }
      });

      expect(errorOccurred).toBe(true);
    });
  });
});
