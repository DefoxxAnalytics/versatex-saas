/**
 * Custom hooks for P2P (Procure-to-Pay) Analytics data from Django API
 *
 * All hooks include organization_id and filters in query keys to properly
 * invalidate cache when switching organizations or filter values change.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  p2pAnalyticsAPI,
  getOrganizationParam,
  ExceptionType,
} from "@/lib/api";
import { useAnalyticsFilters } from "./useAnalytics";
import { queryKeys } from "@/lib/queryKeys";

/**
 * Get the current organization ID for query key inclusion.
 * Returns undefined if viewing own org (default behavior).
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

// =============================================================================
// P2P Cycle Time Analysis Hooks
// =============================================================================

/**
 * Get P2P cycle overview with stage-by-stage metrics
 */
export function useP2PCycleOverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.cycleOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getCycleOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get P2P cycle times by category
 */
export function useP2PCycleByCategory() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.cycleByCategory(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getCycleByCategory(filters);
      return response.data;
    },
  });
}

/**
 * Get P2P cycle times by supplier
 */
export function useP2PCycleBySupplier() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.cycleBySupplier(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getCycleBySupplier(filters);
      return response.data;
    },
  });
}

/**
 * Get P2P cycle time trends over months
 */
export function useP2PCycleTrends(months: number = 12) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.cycleTrends(months, orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getCycleTrends(months, filters);
      return response.data;
    },
  });
}

/**
 * Get P2P bottleneck analysis
 */
export function useP2PBottlenecks() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.bottlenecks(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getBottlenecks(filters);
      return response.data;
    },
  });
}

/**
 * Get P2P process funnel visualization data
 */
export function useP2PProcessFunnel(months: number = 12) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.processFunnel(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getProcessFunnel(months, filters);
      return response.data;
    },
  });
}

/**
 * Get stage drilldown - top slowest items in a specific stage
 */
export function useP2PStageDrilldown(stage: string | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.stageDrilldown(stage || "", orgId, filters),
    queryFn: async () => {
      if (!stage) return null;
      const response = await p2pAnalyticsAPI.getStageDrilldown(stage, filters);
      return response.data;
    },
    enabled: !!stage,
  });
}

// =============================================================================
// 3-Way Matching Hooks
// =============================================================================

/**
 * Get 3-way matching overview metrics
 */
export function useMatchingOverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.matchingOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getMatchingOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get matching exceptions list with filtering
 */
export function useMatchingExceptions(params?: {
  status?: "open" | "resolved" | "all";
  exception_type?: ExceptionType;
  limit?: number;
}) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.matchingExceptions(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getMatchingExceptions(params, filters);
      return response.data;
    },
  });
}

/**
 * Get exceptions breakdown by type
 */
export function useExceptionsByType() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.exceptionsByType(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getExceptionsByType(filters);
      return response.data;
    },
  });
}

/**
 * Get exceptions breakdown by supplier
 */
export function useExceptionsBySupplier() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.exceptionsBySupplier(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getExceptionsBySupplier(filters);
      return response.data;
    },
  });
}

/**
 * Get price variance analysis
 */
export function usePriceVarianceAnalysis() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.priceVariance(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPriceVarianceAnalysis(filters);
      return response.data;
    },
  });
}

/**
 * Get quantity variance analysis
 */
export function useQuantityVarianceAnalysis() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.quantityVariance(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getQuantityVarianceAnalysis(filters);
      return response.data;
    },
  });
}

/**
 * Get invoice match detail for a specific invoice
 */
export function useInvoiceMatchDetail(invoiceId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.invoiceMatchDetail(invoiceId || 0, orgId, filters),
    queryFn: async () => {
      if (!invoiceId) return null;
      const response = await p2pAnalyticsAPI.getInvoiceMatchDetail(invoiceId, filters);
      return response.data;
    },
    enabled: !!invoiceId,
  });
}

/**
 * Resolve a single invoice exception
 */
export function useResolveException() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async ({
      invoiceId,
      resolutionNotes,
    }: {
      invoiceId: number;
      resolutionNotes: string;
    }) => {
      const response = await p2pAnalyticsAPI.resolveException(
        invoiceId,
        resolutionNotes,
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate matching-related queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.matchingOverview(orgId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.p2p.matchingExceptions(orgId) });
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.exceptionsByType(orgId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.exceptionsBySupplier(orgId),
      });
    },
  });
}

/**
 * Bulk resolve multiple invoice exceptions
 */
export function useBulkResolveExceptions() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async ({
      invoiceIds,
      resolutionNotes,
    }: {
      invoiceIds: number[];
      resolutionNotes: string;
    }) => {
      const response = await p2pAnalyticsAPI.bulkResolveExceptions(
        invoiceIds,
        resolutionNotes,
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate matching-related queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.matchingOverview(orgId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.p2p.matchingExceptions(orgId) });
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.exceptionsByType(orgId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.p2p.exceptionsBySupplier(orgId),
      });
    },
  });
}

// =============================================================================
// Invoice Aging / AP Analysis Hooks
// =============================================================================

/**
 * Get aging overview with bucket totals
 */
export function useAgingOverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.agingOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getAgingOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get aging breakdown by supplier
 */
export function useAgingBySupplier() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.agingBySupplier(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getAgingBySupplier(filters);
      return response.data;
    },
  });
}

/**
 * Get payment terms compliance analysis
 */
export function usePaymentTermsCompliance() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.paymentTermsCompliance(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPaymentTermsCompliance(filters);
      return response.data;
    },
  });
}

/**
 * Get DPO trends over time
 */
export function useDPOTrends(months: number = 12) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.dpoTrends(months, orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getDPOTrends(months, filters);
      return response.data;
    },
  });
}

/**
 * Get cash flow forecast
 */
export function useCashFlowForecast(weeks: number = 4) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.cashForecast(weeks, orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getCashFlowForecast(weeks, filters);
      return response.data;
    },
  });
}

// =============================================================================
// Purchase Requisition Hooks
// =============================================================================

/**
 * Get PR overview metrics
 */
export function usePROverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.prOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPROverview(filters);
      return response.data;
    },
  });
}

/**
 * Get PR approval analysis
 */
export function usePRApprovalAnalysis() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.prApprovalAnalysis(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPRApprovalAnalysis(filters);
      return response.data;
    },
  });
}

/**
 * Get PRs by department
 */
export function usePRByDepartment() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.prByDepartment(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPRByDepartment(filters);
      return response.data;
    },
  });
}

/**
 * Get pending PR approvals
 */
export function usePRPending(limit: number = 50) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.prPending(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPRPending(limit, filters);
      return response.data;
    },
  });
}

/**
 * Get PR detail
 */
export function usePRDetail(prId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.prDetail(prId ?? 0, orgId, filters),
    queryFn: async () => {
      if (!prId) return null;
      const response = await p2pAnalyticsAPI.getPRDetail(prId, filters);
      return response.data;
    },
    enabled: !!prId,
  });
}

// =============================================================================
// Purchase Order Hooks
// =============================================================================

/**
 * Get PO overview metrics
 */
export function usePOOverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.poOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPOOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get PO leakage (maverick spend) analysis
 */
export function usePOLeakage() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.poLeakage(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPOLeakage(filters);
      return response.data;
    },
  });
}

/**
 * Get PO amendment analysis
 */
export function usePOAmendments() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.poAmendments(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPOAmendments(filters);
      return response.data;
    },
  });
}

/**
 * Get POs by supplier
 */
export function usePOBySupplier() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.poBySupplier(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getPOBySupplier(filters);
      return response.data;
    },
  });
}

/**
 * Get PO detail
 */
export function usePODetail(poId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.poDetail(poId ?? 0, orgId, filters),
    queryFn: async () => {
      if (!poId) return null;
      const response = await p2pAnalyticsAPI.getPODetail(poId, filters);
      return response.data;
    },
    enabled: !!poId,
  });
}

// =============================================================================
// Supplier Payment Performance Hooks
// =============================================================================

/**
 * Get supplier payments overview
 */
export function useSupplierPaymentsOverview() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.supplierPaymentsOverview(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getSupplierPaymentsOverview(filters);
      return response.data;
    },
  });
}

/**
 * Get supplier payments scorecard
 */
export function useSupplierPaymentsScorecard(limit: number = 50) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.supplierPaymentsScorecard(orgId, filters),
    queryFn: async () => {
      const response = await p2pAnalyticsAPI.getSupplierPaymentsScorecard(
        limit,
        filters,
      );
      return response.data;
    },
  });
}

/**
 * Get supplier payment detail
 */
export function useSupplierPaymentDetail(supplierId: number | null) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.supplierPaymentDetail(supplierId ?? 0, orgId, filters),
    queryFn: async () => {
      if (!supplierId) return null;
      const response = await p2pAnalyticsAPI.getSupplierPaymentDetail(
        supplierId,
        filters,
      );
      return response.data;
    },
    enabled: !!supplierId,
  });
}

/**
 * Get supplier payment history
 */
export function useSupplierPaymentHistory(
  supplierId: number | null,
  months: number = 12,
) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.p2p.supplierPaymentHistory(supplierId ?? 0, orgId, filters),
    queryFn: async () => {
      if (!supplierId) return null;
      const response = await p2pAnalyticsAPI.getSupplierPaymentHistory(
        supplierId,
        months,
        filters,
      );
      return response.data;
    },
    enabled: !!supplierId,
  });
}
