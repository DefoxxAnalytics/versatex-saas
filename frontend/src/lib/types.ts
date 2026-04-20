/**
 * Centralized type definitions for Versatex Analytics
 *
 * This file serves as the single source of truth for API types.
 * When openapi-typescript is configured, types will be auto-generated
 * from the backend OpenAPI schema at /api/schema/
 *
 * Usage:
 *   import type { User, Supplier, Transaction } from '@/lib/types';
 *
 * To regenerate types from backend:
 *   pnpm generate-types
 *
 * @module types
 */

// =============================================================================
// Re-export all types from api.ts for now
// Once openapi-typescript is generating types, this will import from
// api-types.generated.ts instead
// =============================================================================

// Core types
export type { UserRole, UploadStatus } from "./api";

// Organization types
export type { Organization, OrganizationMembership } from "./api";

// User types
export type {
  User,
  UserProfile,
  UserPreferences,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  ChangePasswordRequest,
} from "./api";

// Supplier types
export type {
  Supplier,
  SupplierCreateRequest,
  SupplierUpdateRequest,
  SupplierDetail,
  SupplierSummary,
  SupplierAnalysis,
} from "./api";

// Category types
export type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryDetail,
  SubcategoryDetail,
} from "./api";

// Transaction types
export type {
  Transaction,
  TransactionCreateRequest,
  TransactionUpdateRequest,
  TransactionQueryParams,
} from "./api";

// Upload types
export type {
  DataUpload,
  UploadError,
  CSVUploadResponse,
  BulkDeleteRequest,
  BulkDeleteResponse,
} from "./api";

// Analytics types - Overview
export type {
  OverviewStats,
  SpendByCategory,
  SpendBySupplier,
  MonthlyTrend,
} from "./api";

// Analytics types - Pareto
export type {
  ParetoItem,
  DrilldownBreakdownItem,
  SupplierDrilldown,
} from "./api";

// Analytics types - Tail Spend
export type {
  TailSpendSupplier,
  TailSpendAnalysis,
  TailSpendSummary,
  TailSpendSegment,
  TailSpendSegments,
  TailSpendParetoItem,
  TailSpendCategoryItem,
  TailSpendMultiCategoryVendor,
  TailSpendCategoryConsolidation,
  TailSpendGeographicConsolidation,
  TailSpendConsolidation,
  DetailedTailSpend,
  TailSpendVendorItem,
  TailSpendCategoryDrilldown,
  TailSpendVendorCategory,
  TailSpendVendorLocation,
  TailSpendVendorMonthly,
  TailSpendVendorDrilldown,
} from "./api";

// Analytics types - Stratification
export type {
  StratificationCategory,
  SpendStratification,
  SpendBandData,
  SegmentData,
  StratificationSummary,
  DetailedStratification,
  SegmentSupplier,
  SegmentBreakdownItem,
  SegmentDrilldown,
  BandSupplier,
  BandBreakdownItem,
  BandDrilldown,
} from "./api";

// Analytics types - Seasonality
export type {
  SeasonalityData,
  SeasonalityMonthData,
  CategorySeasonality,
  DetailedSeasonalitySummary,
  DetailedSeasonality,
  SeasonalitySupplier,
  SeasonalityMonthTotal,
  SeasonalityCategoryDrilldown,
} from "./api";

// Analytics types - Year over Year
export type {
  YearOverYearData,
  YoYSummary,
  YoYMonthlyComparison,
  YoYCategoryComparison,
  YoYSupplierComparison,
} from "./api";

// Report types
export type {
  ReportType,
  ReportFormat,
  ReportStatus,
  ScheduleFrequency,
  ReportTemplate,
  ReportListItem,
  ReportDetail,
  ReportGenerateRequest,
  ReportGenerateResponse,
  ReportPreviewData,
  ReportScheduleRequest,
  ReportShareRequest,
  ReportStatusResponse,
  ReportListResponse,
} from "./api";

// Compliance types
export type {
  MaverickRecommendation,
  MaverickSpendAnalysis,
  PolicyViolation,
  ViolationTrendMonth,
  ViolationTrends,
  SupplierComplianceScore,
  SpendingPolicy,
} from "./api";

// Pagination types
export type {
  PaginatedResponse,
  PaginationParams,
  SupplierQueryParams,
  CategoryQueryParams,
  ExportParams,
} from "./api";

// P2P types - Status enums
export type {
  PRStatus,
  PRPriority,
  POStatus,
  GRStatus,
  InvoiceStatus,
  MatchStatus,
  ExceptionType,
} from "./api";

// P2P types - Cycle Time
export type {
  P2PCycleStage,
  P2PCycleOverview,
  P2PCycleByCategory,
  P2PCycleBySupplier,
  P2PCycleTrend,
  P2PBottleneck,
  P2PBottleneckAnalysis,
  P2PFunnelStage,
  P2PProcessFunnel,
  P2PStageDrilldownItem,
  P2PStageDrilldown,
} from "./api";

// P2P types - Matching
export type {
  MatchingOverview,
  InvoiceException,
  ExceptionsByType,
  ExceptionsBySupplier,
  PriceVarianceItem,
  PriceVarianceAnalysis,
  QuantityVarianceItem,
  QuantityVarianceAnalysis,
  InvoiceMatchDetail,
  ExceptionResolution,
  BulkExceptionResolution,
} from "./api";

// P2P types - Aging
export type {
  AgingBucket,
  AgingOverview,
  AgingBySupplier,
  PaymentTermsCompliance,
  DPOTrend,
  CashFlowForecastWeek,
  CashFlowForecast,
} from "./api";

// P2P types - Requisitions
export type {
  PROverview,
  PRApprovalAnalysis,
  PRByDepartment,
  PRPendingItem,
  PRDetail,
} from "./api";

// P2P types - Purchase Orders
export type {
  POOverview,
  POLeakageCategory,
  POLeakage,
  POAmendmentAnalysis,
  POBySupplier,
  PODetail,
} from "./api";

// P2P types - Supplier Payments
export type {
  SupplierPaymentsOverview,
  SupplierPaymentScore,
  SupplierPaymentDetail,
  SupplierPaymentHistoryMonth,
  SupplierPaymentHistoryItem,
  SupplierPaymentHistory,
} from "./api";

// =============================================================================
// Type Utilities
// =============================================================================

/**
 * Extract the data type from a paginated response
 */
export type PaginatedData<T, U> = T extends { results: U[] } ? U : never;

/**
 * Make all properties of T optional except for K
 */
export type PartialExcept<T, K extends keyof T> = Partial<T> & Pick<T, K>;

/**
 * Make properties K of T required
 */
export type RequiredProps<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Extract the element type from an array type
 */
export type ArrayElement<T> = T extends readonly (infer U)[] ? U : never;

// =============================================================================
// Future: OpenAPI generated types
// =============================================================================
// When openapi-typescript is configured and generating types:
//
// 1. Run: pnpm generate-types
// 2. This will create: src/lib/api-types.generated.ts
// 3. Update this file to import from the generated file:
//
//    export type { paths, components, operations } from './api-types.generated';
//    export type User = components['schemas']['User'];
//    export type Supplier = components['schemas']['Supplier'];
//    etc.
//
// This approach provides:
// - Stable import paths (always import from '@/lib/types')
// - Type safety from backend schema
// - Automatic sync when backend changes
// =============================================================================
