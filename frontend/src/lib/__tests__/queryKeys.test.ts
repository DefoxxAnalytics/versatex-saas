/**
 * Tests for Query Key Factory (lib/queryKeys.ts)
 *
 * Tests cover:
 * - Query key structure and format
 * - Organization-scoped keys
 * - Parameterized key generation
 * - Key uniqueness and consistency
 * - All key domains (procurement, analytics, p2p, reports, etc.)
 */

import { describe, it, expect } from "vitest";
import { queryKeys } from "../queryKeys";

describe("Query Keys Factory", () => {
  // =====================
  // Procurement Keys
  // =====================
  describe("procurement", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.procurement.all).toEqual(["procurement"]);
    });

    it("should generate data key with orgId", () => {
      const key = queryKeys.procurement.data(123);
      expect(key).toEqual(["procurement", "data", { orgId: 123 }]);
    });

    it("should generate data key without orgId", () => {
      const key = queryKeys.procurement.data();
      expect(key).toEqual(["procurement", "data", { orgId: undefined }]);
    });

    it("should generate filtered key with orgId", () => {
      const key = queryKeys.procurement.filtered(456);
      expect(key).toEqual(["procurement", "filtered", { orgId: 456 }]);
    });

    describe("suppliers", () => {
      it('should have correct "all" key', () => {
        expect(queryKeys.procurement.suppliers.all).toEqual([
          "procurement",
          "suppliers",
        ]);
      });

      it("should generate list key with params and orgId", () => {
        const params = { page: 1, search: "acme" };
        const key = queryKeys.procurement.suppliers.list(params, 1);
        expect(key).toEqual([
          "procurement",
          "suppliers",
          "list",
          params,
          { orgId: 1 },
        ]);
      });

      it("should generate detail key", () => {
        const key = queryKeys.procurement.suppliers.detail(42, 1);
        expect(key).toEqual([
          "procurement",
          "suppliers",
          "detail",
          42,
          { orgId: 1 },
        ]);
      });
    });

    describe("categories", () => {
      it('should have correct "all" key', () => {
        expect(queryKeys.procurement.categories.all).toEqual([
          "procurement",
          "categories",
        ]);
      });

      it("should generate list key", () => {
        const key = queryKeys.procurement.categories.list(
          { is_active: true },
          1,
        );
        expect(key).toEqual([
          "procurement",
          "categories",
          "list",
          { is_active: true },
          { orgId: 1 },
        ]);
      });

      it("should generate detail key", () => {
        const key = queryKeys.procurement.categories.detail(10, 2);
        expect(key).toEqual([
          "procurement",
          "categories",
          "detail",
          10,
          { orgId: 2 },
        ]);
      });
    });

    describe("transactions", () => {
      it('should have correct "all" key', () => {
        expect(queryKeys.procurement.transactions.all).toEqual([
          "procurement",
          "transactions",
        ]);
      });

      it("should generate list key with filters", () => {
        const params = { supplier: 1, start_date: "2024-01-01" };
        const key = queryKeys.procurement.transactions.list(params, 1);
        expect(key).toEqual([
          "procurement",
          "transactions",
          "list",
          params,
          { orgId: 1 },
        ]);
      });

      it("should generate detail key", () => {
        const key = queryKeys.procurement.transactions.detail(100, 1);
        expect(key).toEqual([
          "procurement",
          "transactions",
          "detail",
          100,
          { orgId: 1 },
        ]);
      });
    });

    describe("uploads", () => {
      it('should have correct "all" key', () => {
        expect(queryKeys.procurement.uploads.all).toEqual([
          "procurement",
          "uploads",
        ]);
      });

      it("should generate list key", () => {
        const key = queryKeys.procurement.uploads.list(1);
        expect(key).toEqual(["procurement", "uploads", "list", { orgId: 1 }]);
      });

      it("should generate detail key", () => {
        const key = queryKeys.procurement.uploads.detail(5, 1);
        expect(key).toEqual([
          "procurement",
          "uploads",
          "detail",
          5,
          { orgId: 1 },
        ]);
      });
    });
  });

  // =====================
  // Analytics Keys
  // =====================
  describe("analytics", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.analytics.all).toEqual(["analytics"]);
    });

    it("should generate overview key", () => {
      const key = queryKeys.analytics.overview(1);
      expect(key).toEqual(["analytics", "overview", { orgId: 1 }]);
    });

    it("should generate spendByCategory key", () => {
      const key = queryKeys.analytics.spendByCategory(1);
      expect(key).toEqual(["analytics", "spend-by-category", { orgId: 1 }]);
    });

    it("should generate spendBySupplier key", () => {
      const key = queryKeys.analytics.spendBySupplier(1);
      expect(key).toEqual(["analytics", "spend-by-supplier", { orgId: 1 }]);
    });

    it("should generate monthlyTrend key with months", () => {
      const key = queryKeys.analytics.monthlyTrend(12, 1);
      expect(key).toEqual(["analytics", "monthly-trend", 12, { orgId: 1 }]);
    });

    describe("Pareto Analysis", () => {
      it("should generate pareto key", () => {
        const key = queryKeys.analytics.pareto(1);
        expect(key).toEqual(["analytics", "pareto", { orgId: 1 }]);
      });

      it("should generate paretoDetailed key", () => {
        const key = queryKeys.analytics.paretoDetailed(1);
        expect(key).toEqual(["analytics", "pareto-detailed", { orgId: 1 }]);
      });

      it("should generate paretoDrilldown key with supplierId", () => {
        const key = queryKeys.analytics.paretoDrilldown(42, 1);
        expect(key).toEqual([
          "analytics",
          "pareto-drilldown",
          42,
          { orgId: 1 },
        ]);
      });
    });

    describe("Detailed Views", () => {
      it("should generate categoryDetails key", () => {
        const key = queryKeys.analytics.categoryDetails(1);
        expect(key).toEqual(["analytics", "category-details", { orgId: 1 }]);
      });

      it("should generate supplierDetails key", () => {
        const key = queryKeys.analytics.supplierDetails(1);
        expect(key).toEqual(["analytics", "supplier-details", { orgId: 1 }]);
      });
    });

    describe("Drilldowns", () => {
      it("should generate supplierDrilldown key", () => {
        const key = queryKeys.analytics.supplierDrilldown(1, 1);
        expect(key).toEqual([
          "analytics",
          "supplier-drilldown",
          1,
          { orgId: 1 },
        ]);
      });

      it("should generate categoryDrilldown key", () => {
        const key = queryKeys.analytics.categoryDrilldown(2, 1);
        expect(key).toEqual([
          "analytics",
          "category-drilldown",
          2,
          { orgId: 1 },
        ]);
      });

      it("should generate segmentDrilldown key", () => {
        const key = queryKeys.analytics.segmentDrilldown("strategic", 1);
        expect(key).toEqual([
          "analytics",
          "segment-drilldown",
          "strategic",
          { orgId: 1 },
        ]);
      });

      it("should generate bandDrilldown key", () => {
        const key = queryKeys.analytics.bandDrilldown("$10K-$50K", 1);
        expect(key).toEqual([
          "analytics",
          "band-drilldown",
          "$10K-$50K",
          { orgId: 1 },
        ]);
      });
    });

    describe("Stratification", () => {
      it("should generate stratification key", () => {
        const key = queryKeys.analytics.stratification(1);
        expect(key).toEqual(["analytics", "stratification", { orgId: 1 }]);
      });

      it("should generate stratificationDetailed key", () => {
        const key = queryKeys.analytics.stratificationDetailed(1);
        expect(key).toEqual([
          "analytics",
          "stratification-detailed",
          { orgId: 1 },
        ]);
      });

      it("should generate stratificationSegment key", () => {
        const key = queryKeys.analytics.stratificationSegment("leverage", 1);
        expect(key).toEqual([
          "analytics",
          "stratification-segment",
          "leverage",
          { orgId: 1 },
        ]);
      });

      it("should generate stratificationBand key", () => {
        const key = queryKeys.analytics.stratificationBand("$1M+", 1);
        expect(key).toEqual([
          "analytics",
          "stratification-band",
          "$1M+",
          { orgId: 1 },
        ]);
      });
    });

    describe("Seasonality", () => {
      it("should generate seasonality key with fiscal year flag", () => {
        const key = queryKeys.analytics.seasonality(true, 1);
        expect(key).toEqual(["analytics", "seasonality", true, { orgId: 1 }]);
      });

      it("should generate seasonality key with calendar year", () => {
        const key = queryKeys.analytics.seasonality(false, 1);
        expect(key).toEqual(["analytics", "seasonality", false, { orgId: 1 }]);
      });

      it("should generate seasonalityDetailed key", () => {
        const key = queryKeys.analytics.seasonalityDetailed(true, 1);
        expect(key).toEqual([
          "analytics",
          "seasonality-detailed",
          true,
          { orgId: 1 },
        ]);
      });

      it("should generate seasonalityCategoryDrilldown key", () => {
        const key = queryKeys.analytics.seasonalityCategoryDrilldown(
          5,
          true,
          1,
        );
        expect(key).toEqual([
          "analytics",
          "seasonality-category",
          5,
          true,
          { orgId: 1 },
        ]);
      });
    });

    describe("Year over Year", () => {
      it("should generate yearOverYear key with all params", () => {
        const key = queryKeys.analytics.yearOverYear(true, 2023, 2024, 1);
        expect(key).toEqual([
          "analytics",
          "yoy",
          true,
          2023,
          2024,
          { orgId: 1 },
        ]);
      });

      it("should generate yoyDetailed key", () => {
        const key = queryKeys.analytics.yoyDetailed(false, 2022, 2023, 1);
        expect(key).toEqual([
          "analytics",
          "yoy-detailed",
          false,
          2022,
          2023,
          { orgId: 1 },
        ]);
      });

      it("should generate yoyCategoryDrilldown key", () => {
        const key = queryKeys.analytics.yoyCategoryDrilldown(
          3,
          true,
          2023,
          2024,
          1,
        );
        expect(key).toEqual([
          "analytics",
          "yoy-category",
          3,
          true,
          2023,
          2024,
          { orgId: 1 },
        ]);
      });

      it("should generate yoySupplierDrilldown key", () => {
        const key = queryKeys.analytics.yoySupplierDrilldown(
          7,
          false,
          2022,
          2023,
          1,
        );
        expect(key).toEqual([
          "analytics",
          "yoy-supplier",
          7,
          false,
          2022,
          2023,
          { orgId: 1 },
        ]);
      });
    });

    describe("Tail Spend", () => {
      it("should generate tailSpend key with threshold", () => {
        const key = queryKeys.analytics.tailSpend(50000, 1);
        expect(key).toEqual(["analytics", "tail-spend", 50000, { orgId: 1 }]);
      });

      it("should generate tailSpendDetailed key", () => {
        const key = queryKeys.analytics.tailSpendDetailed(100000, 1);
        expect(key).toEqual([
          "analytics",
          "tail-spend-detailed",
          100000,
          { orgId: 1 },
        ]);
      });

      it("should generate tailSpendCategoryDrilldown key", () => {
        const key = queryKeys.analytics.tailSpendCategoryDrilldown(1, 50000, 1);
        expect(key).toEqual([
          "analytics",
          "tail-spend-category",
          1,
          50000,
          { orgId: 1 },
        ]);
      });

      it("should generate tailSpendVendorDrilldown key", () => {
        const key = queryKeys.analytics.tailSpendVendorDrilldown(2, 50000, 1);
        expect(key).toEqual([
          "analytics",
          "tail-spend-vendor",
          2,
          50000,
          { orgId: 1 },
        ]);
      });
    });

    describe("Consolidation", () => {
      it("should generate consolidation key", () => {
        const key = queryKeys.analytics.consolidation(1);
        expect(key).toEqual(["analytics", "consolidation", { orgId: 1 }]);
      });
    });
  });

  // =====================
  // P2P Analytics Keys
  // =====================
  describe("p2p", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.p2p.all).toEqual(["p2p"]);
    });

    describe("Cycle Time", () => {
      it("should generate cycleOverview key", () => {
        const key = queryKeys.p2p.cycleOverview(1);
        expect(key).toEqual(["p2p", "cycle-overview", { orgId: 1 }]);
      });

      it("should generate cycleByCategory key", () => {
        const key = queryKeys.p2p.cycleByCategory(1);
        expect(key).toEqual(["p2p", "cycle-by-category", { orgId: 1 }]);
      });

      it("should generate cycleBySupplier key", () => {
        const key = queryKeys.p2p.cycleBySupplier(1);
        expect(key).toEqual(["p2p", "cycle-by-supplier", { orgId: 1 }]);
      });

      it("should generate cycleTrends key with months", () => {
        const key = queryKeys.p2p.cycleTrends(12, 1);
        expect(key).toEqual(["p2p", "cycle-trends", 12, { orgId: 1 }]);
      });

      it("should generate bottlenecks key", () => {
        const key = queryKeys.p2p.bottlenecks(1);
        expect(key).toEqual(["p2p", "bottlenecks", { orgId: 1 }]);
      });

      it("should generate processFunnel key", () => {
        const key = queryKeys.p2p.processFunnel(1);
        expect(key).toEqual(["p2p", "process-funnel", { orgId: 1 }]);
      });

      it("should generate stageDrilldown key", () => {
        const key = queryKeys.p2p.stageDrilldown("pr_to_po", 1);
        expect(key).toEqual([
          "p2p",
          "stage-drilldown",
          "pr_to_po",
          { orgId: 1 },
        ]);
      });
    });

    describe("Matching", () => {
      it("should generate matchingOverview key", () => {
        const key = queryKeys.p2p.matchingOverview(1);
        expect(key).toEqual(["p2p", "matching-overview", { orgId: 1 }]);
      });

      it("should generate matchingExceptions key", () => {
        const key = queryKeys.p2p.matchingExceptions(1);
        expect(key).toEqual(["p2p", "matching-exceptions", { orgId: 1 }]);
      });

      it("should generate exceptionsByType key", () => {
        const key = queryKeys.p2p.exceptionsByType(1);
        expect(key).toEqual(["p2p", "exceptions-by-type", { orgId: 1 }]);
      });

      it("should generate exceptionsBySupplier key", () => {
        const key = queryKeys.p2p.exceptionsBySupplier(1);
        expect(key).toEqual(["p2p", "exceptions-by-supplier", { orgId: 1 }]);
      });

      it("should generate priceVariance key", () => {
        const key = queryKeys.p2p.priceVariance(1);
        expect(key).toEqual(["p2p", "price-variance", { orgId: 1 }]);
      });

      it("should generate quantityVariance key", () => {
        const key = queryKeys.p2p.quantityVariance(1);
        expect(key).toEqual(["p2p", "quantity-variance", { orgId: 1 }]);
      });

      it("should generate invoiceMatchDetail key", () => {
        const key = queryKeys.p2p.invoiceMatchDetail(123, 1);
        expect(key).toEqual(["p2p", "invoice-match", 123, { orgId: 1 }]);
      });
    });

    describe("Aging", () => {
      it("should generate agingOverview key", () => {
        const key = queryKeys.p2p.agingOverview(1);
        expect(key).toEqual(["p2p", "aging-overview", { orgId: 1 }]);
      });

      it("should generate agingBySupplier key", () => {
        const key = queryKeys.p2p.agingBySupplier(1);
        expect(key).toEqual(["p2p", "aging-by-supplier", { orgId: 1 }]);
      });

      it("should generate paymentTermsCompliance key", () => {
        const key = queryKeys.p2p.paymentTermsCompliance(1);
        expect(key).toEqual(["p2p", "payment-terms-compliance", { orgId: 1 }]);
      });

      it("should generate dpoTrends key with months", () => {
        const key = queryKeys.p2p.dpoTrends(6, 1);
        expect(key).toEqual(["p2p", "dpo-trends", 6, { orgId: 1 }]);
      });

      it("should generate cashForecast key with weeks", () => {
        const key = queryKeys.p2p.cashForecast(4, 1);
        expect(key).toEqual(["p2p", "cash-forecast", 4, { orgId: 1 }]);
      });
    });

    describe("Requisitions", () => {
      it("should generate prOverview key", () => {
        const key = queryKeys.p2p.prOverview(1);
        expect(key).toEqual(["p2p", "pr-overview", { orgId: 1 }]);
      });

      it("should generate prApprovalAnalysis key", () => {
        const key = queryKeys.p2p.prApprovalAnalysis(1);
        expect(key).toEqual(["p2p", "pr-approval-analysis", { orgId: 1 }]);
      });

      it("should generate prByDepartment key", () => {
        const key = queryKeys.p2p.prByDepartment(1);
        expect(key).toEqual(["p2p", "pr-by-department", { orgId: 1 }]);
      });

      it("should generate prPending key", () => {
        const key = queryKeys.p2p.prPending(1);
        expect(key).toEqual(["p2p", "pr-pending", { orgId: 1 }]);
      });

      it("should generate prDetail key", () => {
        const key = queryKeys.p2p.prDetail(100, 1);
        expect(key).toEqual(["p2p", "pr-detail", 100, { orgId: 1 }]);
      });
    });

    describe("Purchase Orders", () => {
      it("should generate poOverview key", () => {
        const key = queryKeys.p2p.poOverview(1);
        expect(key).toEqual(["p2p", "po-overview", { orgId: 1 }]);
      });

      it("should generate poLeakage key", () => {
        const key = queryKeys.p2p.poLeakage(1);
        expect(key).toEqual(["p2p", "po-leakage", { orgId: 1 }]);
      });

      it("should generate poAmendments key", () => {
        const key = queryKeys.p2p.poAmendments(1);
        expect(key).toEqual(["p2p", "po-amendments", { orgId: 1 }]);
      });

      it("should generate poBySupplier key", () => {
        const key = queryKeys.p2p.poBySupplier(1);
        expect(key).toEqual(["p2p", "po-by-supplier", { orgId: 1 }]);
      });

      it("should generate poDetail key", () => {
        const key = queryKeys.p2p.poDetail(50, 1);
        expect(key).toEqual(["p2p", "po-detail", 50, { orgId: 1 }]);
      });
    });

    describe("Supplier Payments", () => {
      it("should generate supplierPaymentsOverview key", () => {
        const key = queryKeys.p2p.supplierPaymentsOverview(1);
        expect(key).toEqual([
          "p2p",
          "supplier-payments-overview",
          { orgId: 1 },
        ]);
      });

      it("should generate supplierPaymentsScorecard key", () => {
        const key = queryKeys.p2p.supplierPaymentsScorecard(1);
        expect(key).toEqual([
          "p2p",
          "supplier-payments-scorecard",
          { orgId: 1 },
        ]);
      });

      it("should generate supplierPaymentDetail key", () => {
        const key = queryKeys.p2p.supplierPaymentDetail(10, 1);
        expect(key).toEqual([
          "p2p",
          "supplier-payment-detail",
          10,
          { orgId: 1 },
        ]);
      });

      it("should generate supplierPaymentHistory key", () => {
        const key = queryKeys.p2p.supplierPaymentHistory(10, 1);
        expect(key).toEqual([
          "p2p",
          "supplier-payment-history",
          10,
          { orgId: 1 },
        ]);
      });
    });
  });

  // =====================
  // Reports Keys
  // =====================
  describe("reports", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.reports.all).toEqual(["reports"]);
    });

    it("should generate templates key", () => {
      const key = queryKeys.reports.templates(1);
      expect(key).toEqual(["reports", "templates", { orgId: 1 }]);
    });

    it("should generate history key with params", () => {
      const params = { status: "completed", limit: 20 };
      const key = queryKeys.reports.history(params, 1);
      expect(key).toEqual(["reports", "history", params, { orgId: 1 }]);
    });

    it("should generate detail key", () => {
      const key = queryKeys.reports.detail("report-uuid-123", 1);
      expect(key).toEqual([
        "reports",
        "detail",
        "report-uuid-123",
        { orgId: 1 },
      ]);
    });

    it("should generate status key", () => {
      const key = queryKeys.reports.status("report-uuid-123", 1);
      expect(key).toEqual([
        "reports",
        "status",
        "report-uuid-123",
        { orgId: 1 },
      ]);
    });

    it("should generate schedules key", () => {
      const key = queryKeys.reports.schedules(1);
      expect(key).toEqual(["reports", "schedules", { orgId: 1 }]);
    });

    it("should generate scheduleDetail key", () => {
      const key = queryKeys.reports.scheduleDetail("schedule-uuid-456", 1);
      expect(key).toEqual([
        "reports",
        "schedule-detail",
        "schedule-uuid-456",
        { orgId: 1 },
      ]);
    });
  });

  // =====================
  // Contracts Keys
  // =====================
  describe("contracts", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.contracts.all).toEqual(["contracts"]);
    });

    it("should generate overview key", () => {
      const key = queryKeys.contracts.overview(1);
      expect(key).toEqual(["contracts", "overview", { orgId: 1 }]);
    });

    it("should generate list key", () => {
      const key = queryKeys.contracts.list(1);
      expect(key).toEqual(["contracts", "list", { orgId: 1 }]);
    });

    it("should generate detail key", () => {
      const key = queryKeys.contracts.detail(25, 1);
      expect(key).toEqual(["contracts", "detail", 25, { orgId: 1 }]);
    });
  });

  // =====================
  // Compliance Keys
  // =====================
  describe("compliance", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.compliance.all).toEqual(["compliance"]);
    });

    it("should generate overview key", () => {
      const key = queryKeys.compliance.overview(1);
      expect(key).toEqual(["compliance", "overview", { orgId: 1 }]);
    });

    it("should generate violations key with params", () => {
      const params = { resolved: false, severity: "high" };
      const key = queryKeys.compliance.violations(params, 1);
      expect(key).toEqual(["compliance", "violations", params, { orgId: 1 }]);
    });

    it("should generate maverick key", () => {
      const key = queryKeys.compliance.maverick(1);
      expect(key).toEqual(["compliance", "maverick", { orgId: 1 }]);
    });
  });

  // =====================
  // AI & Predictive Keys
  // =====================
  describe("ai", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.ai.all).toEqual(["ai"]);
    });

    it("should generate insights key with orgId and filters", () => {
      const filters = { category_ids: [1, 2] };
      const key = queryKeys.ai.insights(1, filters);
      expect(key).toEqual(["ai", "insights", { orgId: 1, filters }]);
    });

    it("should generate insightsCost key with filters", () => {
      const filters = { date_from: "2024-01-01" };
      const key = queryKeys.ai.insightsCost(1, filters);
      expect(key).toEqual(["ai", "insights-cost", { orgId: 1, filters }]);
    });

    it("should generate insightsAnomalies key with sensitivity", () => {
      const key = queryKeys.ai.insightsAnomalies(0.5, 1, undefined);
      expect(key).toEqual(["ai", "insights-anomalies", 0.5, { orgId: 1, filters: undefined }]);
    });
  });

  // =====================
  // Predictions Keys
  // =====================
  describe("predictions", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.predictions.all).toEqual(["predictions"]);
    });

    it("should generate spendingForecast key with months and filters", () => {
      const filters = { supplier_ids: [1, 2] };
      const key = queryKeys.predictions.spendingForecast(6, 1, filters);
      expect(key).toEqual(["predictions", "spending-forecast", 6, { orgId: 1, filters }]);
    });

    it("should generate trendAnalysis key with filters", () => {
      const key = queryKeys.predictions.trendAnalysis(1, undefined);
      expect(key).toEqual(["predictions", "trend-analysis", { orgId: 1, filters: undefined }]);
    });
  });

  // =====================
  // Settings Keys (not org-scoped)
  // =====================
  describe("settings", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.settings.all).toEqual(["settings"]);
    });

    it("should generate user key without orgId", () => {
      const key = queryKeys.settings.user();
      expect(key).toEqual(["settings", "user"]);
    });

    it("should generate preferences key without orgId", () => {
      const key = queryKeys.settings.preferences();
      expect(key).toEqual(["settings", "preferences"]);
    });
  });

  // =====================
  // Auth Keys (not org-scoped)
  // =====================
  describe("auth", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.auth.all).toEqual(["auth"]);
    });

    it("should generate user key without orgId", () => {
      const key = queryKeys.auth.user();
      expect(key).toEqual(["auth", "user"]);
    });

    it("should generate organizations key without orgId", () => {
      const key = queryKeys.auth.organizations();
      expect(key).toEqual(["auth", "organizations"]);
    });
  });

  // =====================
  // Filters Keys (not org-scoped)
  // =====================
  describe("filters", () => {
    it('should have correct "all" key', () => {
      expect(queryKeys.filters.all).toEqual(["filters"]);
    });
  });

  // =====================
  // Key Uniqueness Tests
  // =====================
  describe("Key Uniqueness", () => {
    it("should produce different keys for different organizations", () => {
      const key1 = queryKeys.analytics.overview(1);
      const key2 = queryKeys.analytics.overview(2);

      expect(key1).not.toEqual(key2);
      expect(JSON.stringify(key1)).not.toEqual(JSON.stringify(key2));
    });

    it("should produce different keys for different suppliers", () => {
      const key1 = queryKeys.analytics.supplierDrilldown(1, 1);
      const key2 = queryKeys.analytics.supplierDrilldown(2, 1);

      expect(key1).not.toEqual(key2);
    });

    it("should produce different keys for different thresholds", () => {
      const key1 = queryKeys.analytics.tailSpend(50000, 1);
      const key2 = queryKeys.analytics.tailSpend(100000, 1);

      expect(key1).not.toEqual(key2);
    });

    it("should produce different keys for fiscal vs calendar year", () => {
      const key1 = queryKeys.analytics.seasonality(true, 1);
      const key2 = queryKeys.analytics.seasonality(false, 1);

      expect(key1).not.toEqual(key2);
    });
  });

  // =====================
  // Key Consistency Tests
  // =====================
  describe("Key Consistency", () => {
    it("should produce same key for same parameters", () => {
      const key1 = queryKeys.analytics.overview(1);
      const key2 = queryKeys.analytics.overview(1);

      expect(key1).toEqual(key2);
      expect(JSON.stringify(key1)).toEqual(JSON.stringify(key2));
    });

    it("should produce same key for same complex parameters", () => {
      const params = { page: 1, search: "test" };
      const key1 = queryKeys.procurement.suppliers.list(params, 1);
      const key2 = queryKeys.procurement.suppliers.list(params, 1);

      expect(key1).toEqual(key2);
    });
  });

  // =====================
  // Key Structure Tests
  // =====================
  describe("Key Structure", () => {
    it("all keys should be readonly arrays", () => {
      expect(Array.isArray(queryKeys.analytics.all)).toBe(true);
      expect(Array.isArray(queryKeys.procurement.all)).toBe(true);
      expect(Array.isArray(queryKeys.p2p.all)).toBe(true);
      expect(Array.isArray(queryKeys.reports.all)).toBe(true);
    });

    it("org-scoped keys should have orgId in last position", () => {
      const key = queryKeys.analytics.overview(123);
      const lastElement = key[key.length - 1];

      expect(lastElement).toEqual({ orgId: 123 });
    });

    it("parameterized keys should include all parameters", () => {
      const key = queryKeys.analytics.yoyCategoryDrilldown(
        5,
        true,
        2023,
        2024,
        1,
      );

      expect(key).toContain(5); // categoryId
      expect(key).toContain(true); // useFiscalYear
      expect(key).toContain(2023); // year1
      expect(key).toContain(2024); // year2
      expect(key[key.length - 1]).toEqual({ orgId: 1 });
    });
  });
});
