/**
 * Centralized query key factory for React Query.
 *
 * This module provides a single source of truth for all query keys used with
 * TanStack Query. Using a factory pattern ensures:
 * - Consistent key structure across the application
 * - Type-safe query key generation
 * - Easy cache invalidation by key prefix
 * - Organization-scoped keys for multi-tenant support
 *
 * Convention:
 * - All keys are readonly arrays
 * - Organization-scoped keys include orgId as the last element in an object
 * - Use factory functions for parameterized keys
 *
 * Usage:
 *   import { queryKeys } from '@/lib/queryKeys';
 *
 *   // In a hook:
 *   useQuery({
 *     queryKey: queryKeys.analytics.overview(orgId),
 *     queryFn: () => analyticsAPI.getOverview(),
 *   });
 *
 *   // Invalidate all analytics queries:
 *   queryClient.invalidateQueries({ queryKey: queryKeys.analytics.all });
 *
 * @module queryKeys
 */

// Type for analytics filter parameters in query keys
export type FilterParams = {
  date_from?: string;
  date_to?: string;
  supplier_ids?: number[];
  supplier_names?: string[];
  category_ids?: number[];
  category_names?: string[];
  subcategories?: string[];
  locations?: string[];
  years?: number[];
  min_amount?: number;
  max_amount?: number;
};

export const queryKeys = {
  // =========================================================================
  // Procurement
  // =========================================================================
  procurement: {
    all: ["procurement"] as const,
    data: (orgId?: number) => ["procurement", "data", { orgId }] as const,
    filtered: (orgId?: number) =>
      ["procurement", "filtered", { orgId }] as const,
    suppliers: {
      all: ["procurement", "suppliers"] as const,
      list: (params?: Record<string, unknown>, orgId?: number) =>
        ["procurement", "suppliers", "list", params, { orgId }] as const,
      detail: (supplierId: number, orgId?: number) =>
        ["procurement", "suppliers", "detail", supplierId, { orgId }] as const,
    },
    categories: {
      all: ["procurement", "categories"] as const,
      list: (params?: Record<string, unknown>, orgId?: number) =>
        ["procurement", "categories", "list", params, { orgId }] as const,
      detail: (categoryId: number, orgId?: number) =>
        ["procurement", "categories", "detail", categoryId, { orgId }] as const,
    },
    transactions: {
      all: ["procurement", "transactions"] as const,
      list: (params?: Record<string, unknown>, orgId?: number) =>
        ["procurement", "transactions", "list", params, { orgId }] as const,
      detail: (transactionId: number, orgId?: number) =>
        [
          "procurement",
          "transactions",
          "detail",
          transactionId,
          { orgId },
        ] as const,
    },
    uploads: {
      all: ["procurement", "uploads"] as const,
      list: (orgId?: number) =>
        ["procurement", "uploads", "list", { orgId }] as const,
      detail: (uploadId: number, orgId?: number) =>
        ["procurement", "uploads", "detail", uploadId, { orgId }] as const,
    },
  },

  // =========================================================================
  // Analytics - Core
  // =========================================================================
  analytics: {
    all: ["analytics"] as const,
    overview: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "overview", { orgId, filters }] as const,
    spendByCategory: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "spend-by-category", { orgId, filters }] as const,
    spendBySupplier: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "spend-by-supplier", { orgId, filters }] as const,
    monthlyTrend: (months: number, orgId?: number, filters?: FilterParams) =>
      ["analytics", "monthly-trend", months, { orgId, filters }] as const,

    // Pareto Analysis
    pareto: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "pareto", { orgId, filters }] as const,
    paretoDetailed: (orgId?: number) =>
      ["analytics", "pareto-detailed", { orgId }] as const,
    paretoDrilldown: (supplierId: number, orgId?: number) =>
      ["analytics", "pareto-drilldown", supplierId, { orgId }] as const,

    // Detailed views
    categoryDetails: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "category-details", { orgId, filters }] as const,
    supplierDetails: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "supplier-details", { orgId, filters }] as const,

    // Drilldowns
    supplierDrilldown: (supplierId: number, orgId?: number, filters?: FilterParams) =>
      ["analytics", "supplier-drilldown", supplierId, { orgId, filters }] as const,
    categoryDrilldown: (categoryId: number, orgId?: number, filters?: FilterParams) =>
      ["analytics", "category-drilldown", categoryId, { orgId, filters }] as const,
    segmentDrilldown: (segment: string, orgId?: number, filters?: FilterParams) =>
      ["analytics", "segment-drilldown", segment, { orgId, filters }] as const,
    bandDrilldown: (band: string, orgId?: number, filters?: FilterParams) =>
      ["analytics", "band-drilldown", band, { orgId, filters }] as const,

    // Stratification
    stratification: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "stratification", { orgId, filters }] as const,
    stratificationDetailed: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "stratification-detailed", { orgId, filters }] as const,
    stratificationSegment: (segment: string, orgId?: number) =>
      ["analytics", "stratification-segment", segment, { orgId }] as const,
    stratificationBand: (band: string, orgId?: number) =>
      ["analytics", "stratification-band", band, { orgId }] as const,

    // Seasonality
    seasonality: (useFiscalYear: boolean, orgId?: number, filters?: FilterParams) =>
      ["analytics", "seasonality", useFiscalYear, { orgId, filters }] as const,
    seasonalityDetailed: (useFiscalYear: boolean, orgId?: number, filters?: FilterParams) =>
      ["analytics", "seasonality-detailed", useFiscalYear, { orgId, filters }] as const,
    seasonalityCategoryDrilldown: (
      categoryId: number,
      useFiscalYear: boolean,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "seasonality-category",
        categoryId,
        useFiscalYear,
        { orgId, filters },
      ] as const,

    // Year over Year
    yearOverYear: (
      useFiscalYear: boolean,
      year1: number,
      year2: number,
      orgId?: number,
      filters?: FilterParams,
    ) => ["analytics", "yoy", useFiscalYear, year1, year2, { orgId, filters }] as const,
    yoyDetailed: (
      useFiscalYear: boolean,
      year1: number,
      year2: number,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "yoy-detailed",
        useFiscalYear,
        year1,
        year2,
        { orgId, filters },
      ] as const,
    yoyCategoryDrilldown: (
      categoryId: number,
      useFiscalYear: boolean,
      year1: number,
      year2: number,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "yoy-category",
        categoryId,
        useFiscalYear,
        year1,
        year2,
        { orgId, filters },
      ] as const,
    yoySupplierDrilldown: (
      supplierId: number,
      useFiscalYear: boolean,
      year1: number,
      year2: number,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "yoy-supplier",
        supplierId,
        useFiscalYear,
        year1,
        year2,
        { orgId, filters },
      ] as const,

    // Tail Spend
    tailSpend: (threshold: number, orgId?: number, filters?: FilterParams) =>
      ["analytics", "tail-spend", threshold, { orgId, filters }] as const,
    tailSpendDetailed: (threshold: number, orgId?: number, filters?: FilterParams) =>
      ["analytics", "tail-spend-detailed", threshold, { orgId, filters }] as const,
    tailSpendCategoryDrilldown: (
      categoryId: number,
      threshold: number,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "tail-spend-category",
        categoryId,
        threshold,
        { orgId, filters },
      ] as const,
    tailSpendVendorDrilldown: (
      vendorId: number,
      threshold: number,
      orgId?: number,
      filters?: FilterParams,
    ) =>
      [
        "analytics",
        "tail-spend-vendor",
        vendorId,
        threshold,
        { orgId, filters },
      ] as const,

    // Consolidation
    consolidation: (orgId?: number, filters?: FilterParams) =>
      ["analytics", "consolidation", { orgId, filters }] as const,
  },

  // =========================================================================
  // P2P Analytics
  // =========================================================================
  p2p: {
    all: ["p2p"] as const,

    // Cycle Time
    cycleOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "cycle-overview", { orgId, filters }] as const,
    cycleByCategory: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "cycle-by-category", { orgId, filters }] as const,
    cycleBySupplier: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "cycle-by-supplier", { orgId, filters }] as const,
    cycleTrends: (months: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "cycle-trends", months, { orgId, filters }] as const,
    bottlenecks: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "bottlenecks", { orgId, filters }] as const,
    processFunnel: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "process-funnel", { orgId, filters }] as const,
    stageDrilldown: (stage: string, orgId?: number, filters?: FilterParams) =>
      ["p2p", "stage-drilldown", stage, { orgId, filters }] as const,

    // Matching
    matchingOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "matching-overview", { orgId, filters }] as const,
    matchingExceptions: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "matching-exceptions", { orgId, filters }] as const,
    exceptionsByType: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "exceptions-by-type", { orgId, filters }] as const,
    exceptionsBySupplier: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "exceptions-by-supplier", { orgId, filters }] as const,
    priceVariance: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "price-variance", { orgId, filters }] as const,
    quantityVariance: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "quantity-variance", { orgId, filters }] as const,
    invoiceMatchDetail: (invoiceId: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "invoice-match", invoiceId, { orgId, filters }] as const,

    // Aging
    agingOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "aging-overview", { orgId, filters }] as const,
    agingBySupplier: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "aging-by-supplier", { orgId, filters }] as const,
    paymentTermsCompliance: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "payment-terms-compliance", { orgId, filters }] as const,
    dpoTrends: (months: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "dpo-trends", months, { orgId, filters }] as const,
    cashForecast: (weeks: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "cash-forecast", weeks, { orgId, filters }] as const,

    // Requisitions
    prOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "pr-overview", { orgId, filters }] as const,
    prApprovalAnalysis: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "pr-approval-analysis", { orgId, filters }] as const,
    prByDepartment: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "pr-by-department", { orgId, filters }] as const,
    prPending: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "pr-pending", { orgId, filters }] as const,
    prDetail: (prId: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "pr-detail", prId, { orgId, filters }] as const,

    // Purchase Orders
    poOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "po-overview", { orgId, filters }] as const,
    poLeakage: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "po-leakage", { orgId, filters }] as const,
    poAmendments: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "po-amendments", { orgId, filters }] as const,
    poBySupplier: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "po-by-supplier", { orgId, filters }] as const,
    poDetail: (poId: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "po-detail", poId, { orgId, filters }] as const,

    // Supplier Payments
    supplierPaymentsOverview: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "supplier-payments-overview", { orgId, filters }] as const,
    supplierPaymentsScorecard: (orgId?: number, filters?: FilterParams) =>
      ["p2p", "supplier-payments-scorecard", { orgId, filters }] as const,
    supplierPaymentDetail: (supplierId: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "supplier-payment-detail", supplierId, { orgId, filters }] as const,
    supplierPaymentHistory: (supplierId: number, orgId?: number, filters?: FilterParams) =>
      ["p2p", "supplier-payment-history", supplierId, { orgId, filters }] as const,
  },

  // =========================================================================
  // Reports
  // =========================================================================
  reports: {
    all: ["reports"] as const,
    templates: (orgId?: number) => ["reports", "templates", { orgId }] as const,
    history: (params?: Record<string, unknown>, orgId?: number) =>
      ["reports", "history", params, { orgId }] as const,
    detail: (reportId: string, orgId?: number) =>
      ["reports", "detail", reportId, { orgId }] as const,
    status: (reportId: string, orgId?: number) =>
      ["reports", "status", reportId, { orgId }] as const,
    schedules: (orgId?: number) => ["reports", "schedules", { orgId }] as const,
    scheduleDetail: (scheduleId: string, orgId?: number) =>
      ["reports", "schedule-detail", scheduleId, { orgId }] as const,
  },

  // =========================================================================
  // Contracts
  // =========================================================================
  contracts: {
    all: ["contracts"] as const,
    overview: (orgId?: number, filters?: FilterParams) =>
      ["contracts", "overview", { orgId, filters }] as const,
    list: (orgId?: number, filters?: FilterParams) =>
      ["contracts", "list", { orgId, filters }] as const,
    detail: (contractId: number, orgId?: number, filters?: FilterParams) =>
      ["contracts", "detail", contractId, { orgId, filters }] as const,
    expiring: (days: number, orgId?: number, filters?: FilterParams) =>
      ["contracts", "expiring", days, { orgId, filters }] as const,
    performance: (contractId: number, orgId?: number, filters?: FilterParams) =>
      ["contracts", "performance", contractId, { orgId, filters }] as const,
    savings: (orgId?: number, filters?: FilterParams) =>
      ["contracts", "savings", { orgId, filters }] as const,
    renewals: (orgId?: number, filters?: FilterParams) =>
      ["contracts", "renewals", { orgId, filters }] as const,
    vsActual: (contractId: number | undefined, orgId?: number, filters?: FilterParams) =>
      ["contracts", "vs-actual", contractId, { orgId, filters }] as const,
  },

  // =========================================================================
  // Compliance
  // =========================================================================
  compliance: {
    all: ["compliance"] as const,
    overview: (orgId?: number, filters?: FilterParams) =>
      ["compliance", "overview", { orgId, filters }] as const,
    violations: (params?: Record<string, unknown>, orgId?: number, filters?: FilterParams) =>
      ["compliance", "violations", params, { orgId, filters }] as const,
    maverick: (orgId?: number, filters?: FilterParams) =>
      ["compliance", "maverick", { orgId, filters }] as const,
    violationTrends: (months: number, orgId?: number, filters?: FilterParams) =>
      ["compliance", "violation-trends", months, { orgId, filters }] as const,
    supplierScores: (orgId?: number, filters?: FilterParams) =>
      ["compliance", "supplier-scores", { orgId, filters }] as const,
    policies: (orgId?: number, filters?: FilterParams) =>
      ["compliance", "policies", { orgId, filters }] as const,
  },

  // =========================================================================
  // AI Insights
  // =========================================================================
  ai: {
    all: ["ai"] as const,
    insights: (orgId?: number, filters?: FilterParams) =>
      ["ai", "insights", { orgId, filters }] as const,
    insightsCost: (orgId?: number, filters?: FilterParams) =>
      ["ai", "insights-cost", { orgId, filters }] as const,
    insightsRisk: (orgId?: number, filters?: FilterParams) =>
      ["ai", "insights-risk", { orgId, filters }] as const,
    insightsAnomalies: (sensitivity: number, orgId?: number, filters?: FilterParams) =>
      ["ai", "insights-anomalies", sensitivity, { orgId, filters }] as const,
    asyncEnhancementStatus: (orgId?: number) =>
      ["ai", "async-enhancement-status", { orgId }] as const,
    deepAnalysisStatus: (insightId: string | null, orgId?: number) =>
      ["ai", "deep-analysis-status", insightId, { orgId }] as const,
    insightFeedback: (params?: Record<string, unknown>, orgId?: number) =>
      ["ai", "insight-feedback", params, { orgId }] as const,
    insightEffectiveness: (orgId?: number) =>
      ["ai", "insight-effectiveness", { orgId }] as const,
    usageSummary: (days: number, orgId?: number) =>
      ["ai", "usage-summary", days, { orgId }] as const,
    usageDaily: (days: number, orgId?: number) =>
      ["ai", "usage-daily", days, { orgId }] as const,
  },

  // =========================================================================
  // Predictive Analytics
  // =========================================================================
  predictions: {
    all: ["predictions"] as const,
    spendingForecast: (months: number, orgId?: number, filters?: FilterParams) =>
      ["predictions", "spending-forecast", months, { orgId, filters }] as const,
    categoryForecast: (categoryId: number, months: number, orgId?: number, filters?: FilterParams) =>
      ["predictions", "category-forecast", categoryId, months, { orgId, filters }] as const,
    supplierForecast: (supplierId: number, months: number, orgId?: number, filters?: FilterParams) =>
      ["predictions", "supplier-forecast", supplierId, months, { orgId, filters }] as const,
    trendAnalysis: (orgId?: number, filters?: FilterParams) =>
      ["predictions", "trend-analysis", { orgId, filters }] as const,
    budgetProjection: (annualBudget: number, orgId?: number, filters?: FilterParams) =>
      ["predictions", "budget-projection", annualBudget, { orgId, filters }] as const,
  },

  // =========================================================================
  // Settings (not org-scoped)
  // =========================================================================
  settings: {
    all: ["settings"] as const,
    user: () => ["settings", "user"] as const,
    preferences: () => ["settings", "preferences"] as const,
  },

  // =========================================================================
  // Auth (not org-scoped)
  // =========================================================================
  auth: {
    all: ["auth"] as const,
    user: () => ["auth", "user"] as const,
    organizations: () => ["auth", "organizations"] as const,
  },

  // =========================================================================
  // Organization Settings (org-scoped, admin only)
  // =========================================================================
  orgSettings: {
    all: ["orgSettings"] as const,
    savingsConfig: (orgId: number) =>
      ["orgSettings", "savingsConfig", { orgId }] as const,
  },

  // =========================================================================
  // Filters (not org-scoped, stored in localStorage)
  // =========================================================================
  filters: {
    all: ["filters"] as const,
  },
} as const;

// Type exports for consumers
export type QueryKeys = typeof queryKeys;
export type AnalyticsQueryKeys = typeof queryKeys.analytics;
export type P2PQueryKeys = typeof queryKeys.p2p;
export type ReportsQueryKeys = typeof queryKeys.reports;
export type ContractsQueryKeys = typeof queryKeys.contracts;
export type ComplianceQueryKeys = typeof queryKeys.compliance;
export type AIQueryKeys = typeof queryKeys.ai;
export type PredictionsQueryKeys = typeof queryKeys.predictions;
export type OrgSettingsQueryKeys = typeof queryKeys.orgSettings;
