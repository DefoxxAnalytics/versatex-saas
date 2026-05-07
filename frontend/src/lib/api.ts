/**
 * API client for Django backend with typed interfaces
 */
import axios, { AxiosResponse } from "axios";

// =====================
// Type Definitions
// =====================

// Base types
export type UserRole = "admin" | "manager" | "viewer";
export type UploadStatus = "processing" | "completed" | "failed" | "partial";

// Organization
export interface Organization {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
}

// Organization Membership (for multi-org users)
export interface OrganizationMembership {
  id: number;
  organization: number;
  organization_name: string;
  organization_slug: string;
  organization_is_demo: boolean;
  role: UserRole;
  is_primary: boolean;
  is_active: boolean;
  created_at?: string;
}

// User Profile
export interface UserProfile {
  id: number;
  organization: number;
  organization_name: string;
  organization_is_demo?: boolean;
  role: UserRole;
  phone: string;
  department: string;
  is_active: boolean;
  created_at: string;
  is_super_admin: boolean;
  organizations?: OrganizationMembership[]; // Multi-org memberships
}

// User
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  profile: UserProfile;
}

// Authentication
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  organization: number;
  role?: UserRole;
}

// Note: Tokens are now stored in HTTP-only cookies, not returned in response body
export interface AuthResponse {
  user: User;
  message: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
  new_password_confirm: string;
}

// User Preferences
export interface UserPreferences {
  theme?: "light" | "dark" | "system";
  colorScheme?: "navy" | "classic" | "versatex";
  notifications?: boolean;
  exportFormat?: "csv" | "xlsx" | "pdf";
  currency?: string;
  dateFormat?: string;
  dashboardLayout?: Record<string, unknown>;
  sidebarCollapsed?: boolean;
  // AI & Predictive Analytics Settings
  forecastingModel?: "simple_average" | "linear" | "advanced";
  useExternalAI?: boolean;
  aiProvider?: "anthropic" | "openai";
  forecastHorizonMonths?: number;
  anomalySensitivity?: number;
  // Sent plaintext on write; backend returns masked ('****' + last4) on read.
  aiApiKey?: string;
}

// Savings Configuration Types (Industry Benchmark Rates)
export type BenchmarkProfile =
  | "conservative"
  | "moderate"
  | "aggressive"
  | "custom";
export type InsightType =
  | "consolidation"
  | "anomaly"
  | "cost_optimization"
  | "risk";

export interface SavingsConfig {
  benchmark_profile?: BenchmarkProfile;
  consolidation_rate?: number; // 0.005 - 0.15 (0.5% - 15%)
  anomaly_recovery_rate?: number; // 0.001 - 0.05 (0.1% - 5%)
  price_variance_capture?: number; // 0.10 - 0.90 (10% - 90%)
  specification_rate?: number; // 0.005 - 0.10 (0.5% - 10%)
  payment_terms_rate?: number; // 0.001 - 0.03 (0.1% - 3%)
  process_savings_per_txn?: number; // 10 - 100 ($)
  enabled_insights?: InsightType[];
}

export interface SavingsConfigResponse {
  savings_config: SavingsConfig;
  effective_config: Required<SavingsConfig>;
  available_profiles: Record<
    Exclude<BenchmarkProfile, "custom">,
    Omit<SavingsConfig, "benchmark_profile" | "enabled_insights">
  >;
}

// Supplier
export interface Supplier {
  id: number;
  name: string;
  code: string;
  contact_email: string;
  contact_phone: string;
  address: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  transaction_count?: number;
  total_spend?: number;
}

export interface SupplierCreateRequest {
  name: string;
  code?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  is_active?: boolean;
}

export interface SupplierUpdateRequest extends Partial<SupplierCreateRequest> {}

// Category
export interface Category {
  id: number;
  name: string;
  parent: number | null;
  parent_name: string | null;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  transaction_count?: number;
  total_spend?: number;
}

export interface CategoryCreateRequest {
  name: string;
  parent?: number | null;
  description?: string;
  is_active?: boolean;
}

export interface CategoryUpdateRequest extends Partial<CategoryCreateRequest> {}

// Transaction
export interface Transaction {
  id: number;
  supplier: number;
  supplier_name: string;
  category: number;
  category_name: string;
  amount: string;
  date: string;
  description: string;
  subcategory: string;
  location: string;
  fiscal_year: number | null;
  spend_band: string;
  payment_method: string;
  invoice_number: string;
  upload_batch: string;
  uploaded_by: number;
  uploaded_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreateRequest {
  supplier?: number;
  supplier_name?: string;
  category?: number;
  category_name?: string;
  amount: number | string;
  date: string;
  description?: string;
  subcategory?: string;
  location?: string;
  fiscal_year?: number;
  spend_band?: string;
  payment_method?: string;
  invoice_number?: string;
}

export interface TransactionUpdateRequest
  extends Partial<TransactionCreateRequest> {}

export interface BulkDeleteRequest {
  ids: number[];
}

export interface BulkDeleteResponse {
  deleted: number;
  message: string;
}

// Data Upload
export interface DataUpload {
  id: number;
  file_name: string;
  file_size: number;
  batch_id: string;
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  duplicate_rows: number;
  status: UploadStatus;
  error_log: UploadError[];
  uploaded_by: number;
  uploaded_by_name: string;
  created_at: string;
  completed_at: string | null;
}

export interface UploadError {
  row: number;
  error: string;
  data: Record<string, unknown>;
}

export interface CSVUploadResponse {
  upload: DataUpload;
  message: string;
}

// Analytics types

// Filter parameters for analytics API calls
export interface AnalyticsFilters {
  date_from?: string;
  date_to?: string;
  supplier_ids?: number[];
  supplier_names?: string[]; // Names are resolved to IDs server-side
  category_ids?: number[];
  category_names?: string[]; // Names are resolved to IDs server-side
  subcategories?: string[];
  locations?: string[];
  years?: number[];
  min_amount?: number;
  max_amount?: number;
}

// Helper to build filter query params
export function buildFilterParams(
  filters?: AnalyticsFilters,
): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (!filters) return params;

  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  if (filters.supplier_ids?.length)
    params.supplier_ids = filters.supplier_ids.join(",");
  if (filters.supplier_names?.length)
    params.supplier_names = filters.supplier_names.join(",");
  if (filters.category_ids?.length)
    params.category_ids = filters.category_ids.join(",");
  if (filters.category_names?.length)
    params.category_names = filters.category_names.join(",");
  if (filters.subcategories?.length)
    params.subcategories = filters.subcategories.join(",");
  if (filters.locations?.length) params.locations = filters.locations.join(",");
  if (filters.years?.length) params.years = filters.years.join(",");
  if (filters.min_amount !== undefined) params.min_amount = filters.min_amount;
  if (filters.max_amount !== undefined) params.max_amount = filters.max_amount;

  return params;
}

export interface OverviewStats {
  total_spend: number;
  transaction_count: number;
  supplier_count: number;
  category_count: number;
  avg_transaction: number;
}

export interface SpendByCategory {
  category: string;
  category_id: number;
  amount: number;
  count: number;
}

// Detailed category analysis with subcategories and risk levels
export interface SubcategoryDetail {
  name: string;
  spend: number;
  transaction_count: number;
  supplier_count: number;
  percent_of_category: number;
}

export interface CategoryDetail {
  category: string;
  category_id: number;
  total_spend: number;
  percent_of_total: number;
  transaction_count: number;
  subcategory_count: number;
  supplier_count: number;
  avg_spend_per_supplier: number;
  top_subcategory: string;
  top_subcategory_spend: number;
  concentration: number;
  risk_level: "high" | "medium" | "low";
  subcategories: SubcategoryDetail[];
}

export interface SpendBySupplier {
  supplier: string;
  supplier_id: number;
  amount: number;
  count: number;
}

// Detailed supplier analysis with HHI score and concentration metrics
export interface SupplierDetail {
  supplier: string;
  supplier_id: number;
  total_spend: number;
  percent_of_total: number;
  transaction_count: number;
  avg_transaction: number;
  category_count: number;
  rank: number;
}

export interface SupplierSummary {
  total_suppliers: number;
  total_spend: number;
  hhi_score: number;
  hhi_risk_level: "low" | "moderate" | "high";
  top3_concentration: number;
  top_supplier: string | null;
  top_supplier_spend: number;
}

export interface SupplierAnalysis {
  summary: SupplierSummary;
  suppliers: SupplierDetail[];
}

export interface MonthlyTrend {
  month: string;
  amount: number;
  count: number;
}

export interface ParetoItem {
  supplier: string;
  supplier_id: number;
  amount: number;
  cumulative_percentage: number;
}

// Supplier drill-down for Pareto Analysis
export interface DrilldownBreakdownItem {
  name: string;
  spend: number;
  transaction_count: number;
  percent_of_total: number;
}

export interface SupplierDrilldown {
  supplier_id: number;
  supplier_name: string;
  total_spend: number;
  transaction_count: number;
  avg_transaction: number;
  date_range: {
    min: string | null;
    max: string | null;
  };
  categories: DrilldownBreakdownItem[];
  subcategories: DrilldownBreakdownItem[];
  locations: DrilldownBreakdownItem[];
}

export interface DrilldownSupplierItem {
  id: number;
  name: string;
  spend: number;
  transaction_count: number;
  percent_of_total: number;
}

export interface DrilldownRecentTransaction {
  id: number;
  date: string | null;
  amount: number;
  supplier_name: string;
  description: string;
}

export interface CategoryDrilldown {
  category_id: number;
  category_name: string;
  total_spend: number;
  transaction_count: number;
  avg_transaction: number;
  supplier_count: number;
  date_range: {
    min: string | null;
    max: string | null;
  };
  suppliers: DrilldownSupplierItem[];
  subcategories: DrilldownBreakdownItem[];
  locations: DrilldownBreakdownItem[];
  recent_transactions: DrilldownRecentTransaction[];
}

export interface TailSpendSupplier {
  supplier: string;
  supplier_id: number;
  amount: number;
  transaction_count: number;
}

export interface TailSpendAnalysis {
  tail_suppliers: TailSpendSupplier[];
  tail_count: number;
  tail_spend: number;
  tail_percentage: number;
}

// Detailed Tail Spend Types (for TailSpend page)
export interface TailSpendSummary {
  total_vendors: number;
  tail_vendor_count: number;
  tail_spend: number;
  tail_percentage: number;
  total_spend: number;
  savings_opportunity: number;
  vendor_ratio: number;
}

export interface TailSpendSegment {
  count: number;
  spend: number;
  transactions: number;
  avg_spend_per_vendor: number;
}

export interface TailSpendSegments {
  micro: TailSpendSegment;
  small: TailSpendSegment;
  non_tail: TailSpendSegment;
}

export interface TailSpendParetoItem {
  supplier: string;
  supplier_id: number;
  spend: number;
  cumulative_pct: number;
  is_tail: boolean;
}

export interface TailSpendCategoryItem {
  category: string;
  category_id: number | null;
  tail_spend: number;
  tail_vendors: number;
  total_spend: number;
  total_vendors: number;
  tail_percentage: number;
  vendor_percentage: number;
}

export interface TailSpendMultiCategoryVendor {
  supplier: string;
  supplier_id: number;
  categories: string[];
  category_count: number;
  total_spend: number;
  savings_potential: number;
}

export interface TailSpendCategoryConsolidation {
  category: string;
  category_id: number | null;
  tail_vendors: number;
  total_vendors: number;
  tail_spend: number;
  top_vendor: string;
  savings_potential: number;
}

export interface TailSpendGeographicConsolidation {
  location: string;
  tail_vendors: number;
  total_vendors: number;
  tail_spend: number;
  top_vendor: string;
  savings_potential: number;
}

export interface TailSpendConsolidation {
  total_opportunities: number;
  total_savings: number;
  top_type: string;
  multi_category: TailSpendMultiCategoryVendor[];
  category: TailSpendCategoryConsolidation[];
  geographic: TailSpendGeographicConsolidation[];
}

export interface DetailedTailSpend {
  summary: TailSpendSummary;
  segments: TailSpendSegments;
  pareto_data: TailSpendParetoItem[];
  category_analysis: TailSpendCategoryItem[];
  consolidation_opportunities: TailSpendConsolidation;
}

// Tail Spend Category Drilldown
export interface TailSpendVendorItem {
  name: string;
  supplier_id: number;
  spend: number;
  transaction_count: number;
  is_tail: boolean;
  percent_of_category: number;
}

export interface TailSpendCategoryDrilldown {
  category: string;
  category_id: number;
  total_spend: number;
  tail_spend: number;
  tail_percentage: number;
  vendors: TailSpendVendorItem[];
  recommendations: string[];
}

// Tail Spend Vendor Drilldown
export interface TailSpendVendorCategory {
  name: string;
  category_id: number | null;
  spend: number;
  transaction_count: number;
  percent_of_vendor: number;
}

export interface TailSpendVendorLocation {
  name: string;
  spend: number;
  transaction_count: number;
}

export interface TailSpendVendorMonthly {
  month: string;
  spend: number;
}

export interface TailSpendVendorDrilldown {
  supplier: string;
  supplier_id: number;
  total_spend: number;
  transaction_count: number;
  is_tail: boolean;
  categories: TailSpendVendorCategory[];
  locations: TailSpendVendorLocation[];
  monthly_spend: TailSpendVendorMonthly[];
}

export interface StratificationCategory {
  category: string;
  spend: number;
  supplier_count: number;
  transaction_count: number;
}

export interface SpendStratification {
  strategic: StratificationCategory[];
  leverage: StratificationCategory[];
  bottleneck: StratificationCategory[];
  tactical: StratificationCategory[];
}

// Detailed Stratification Types (for SpendStratification page)
export interface SpendBandData {
  band: string;
  label: string;
  min: number;
  max: number | null;
  total_spend: number;
  percent_of_total: number;
  suppliers: number;
  transactions: number;
  avg_spend_per_supplier: number;
  strategic_importance: "Tactical" | "Strategic" | "Critical";
  risk_level: "Low" | "Medium" | "High";
}

export interface SegmentData {
  segment: "Strategic" | "Leverage" | "Routine" | "Tactical";
  spend_range: string;
  min: number;
  max: number | null;
  total_spend: number;
  percent_of_total: number;
  suppliers: number;
  transactions: number;
  strategy: string;
}

export interface StratificationSummary {
  total_spend: number;
  active_spend_bands: number;
  strategic_bands: number;
  high_risk_bands: number;
  complex_bands: number;
  highest_impact_band: string;
  highest_impact_percent: number;
  most_fragmented_band: string;
  most_fragmented_suppliers: number;
  avg_suppliers_per_band: number;
  overall_risk: string;
  recommendations: string[];
}

export interface DetailedStratification {
  summary: StratificationSummary;
  spend_bands: SpendBandData[];
  segments: SegmentData[];
}

export interface SegmentSupplier {
  name: string;
  supplier_id: number;
  total_spend: number;
  percent_of_segment: number;
  transactions: number;
  subcategory_count: number;
  location_count: number;
}

export interface SegmentBreakdownItem {
  name: string;
  spend: number;
  percent_of_segment: number;
  transactions: number;
}

export interface SegmentDrilldown {
  segment: string;
  total_spend: number;
  supplier_count: number;
  transaction_count: number;
  avg_spend_per_supplier: number;
  suppliers: SegmentSupplier[];
  subcategories: SegmentBreakdownItem[];
  locations: SegmentBreakdownItem[];
}

// Band drill-down for SpendStratification (spend band level)
export interface BandSupplier {
  name: string;
  supplier_id: number;
  total_spend: number;
  percent_of_band: number;
  transactions: number;
  subcategory_count: number;
  location_count: number;
}

export interface BandBreakdownItem {
  name: string;
  spend: number;
  percent_of_band: number;
  transactions: number;
}

export interface BandDrilldown {
  band: string;
  total_spend: number;
  supplier_count: number;
  transaction_count: number;
  avg_spend_per_supplier: number;
  suppliers: BandSupplier[];
  subcategories: BandBreakdownItem[];
  locations: BandBreakdownItem[];
}

export interface SeasonalityData {
  month: string;
  average_spend: number;
  occurrences: number;
}

// Detailed Seasonality types for Seasonality dashboard page
export interface SeasonalityMonthData {
  month: string;
  fiscal_month: number;
  years: Record<string, number>; // e.g., { 'FY2024': 1500000, 'FY2025': 1650000 }
  average: number;
}

export interface CategorySeasonality {
  category: string;
  category_id: number | null;
  total_spend: number;
  peak_month: string;
  low_month: string;
  seasonality_strength: number;
  impact_level: "High" | "Medium" | "Low";
  savings_potential: number;
  yoy_growth: number;
  fy_totals: Record<string, number>; // e.g., { 'FY2024': 2200000, 'FY2025': 2800000 }
  monthly_spend: number[]; // 12 values for each fiscal month
  seasonal_indices: number[]; // 12 values normalized to 100
}

export interface DetailedSeasonalitySummary {
  categories_analyzed: number;
  opportunities_found: number;
  high_impact_count: number;
  total_savings_potential: number;
  avg_yoy_growth: number;
  available_years: number[];
}

export interface DetailedSeasonality {
  summary: DetailedSeasonalitySummary;
  monthly_data: SeasonalityMonthData[];
  category_seasonality: CategorySeasonality[];
}

// Seasonality category drill-down types
export interface SeasonalitySupplier {
  name: string;
  supplier_id: number;
  total_spend: number;
  percent_of_category: number;
  monthly_spend: number[]; // 12 values
  peak_month: string;
  low_month: string;
  seasonality_strength: number;
}

export interface SeasonalityMonthTotal {
  month: string;
  spend: number;
}

export interface SeasonalityCategoryDrilldown {
  category: string;
  category_id: number;
  total_spend: number;
  supplier_count: number;
  suppliers: SeasonalitySupplier[];
  monthly_totals: SeasonalityMonthTotal[];
}

export interface YearOverYearData {
  year: number;
  total_spend: number;
  transaction_count: number;
  avg_transaction: number;
  growth_percentage?: number;
}

// Detailed Year-over-Year types
export interface YoYSummary {
  year1: string;
  year2: string;
  year1_total_spend: number;
  year2_total_spend: number;
  spend_change: number;
  spend_change_pct: number;
  year1_transactions: number;
  year2_transactions: number;
  year1_suppliers: number;
  year2_suppliers: number;
  year1_avg_transaction: number;
  year2_avg_transaction: number;
}

export interface YoYMonthlyComparison {
  month: string;
  fiscal_month: number;
  year1_spend: number;
  year2_spend: number;
  change_pct: number;
}

export interface YoYCategoryComparison {
  category: string;
  category_id: number | null;
  year1_spend: number;
  year2_spend: number;
  change: number;
  change_pct: number;
  year1_pct_of_total: number;
  year2_pct_of_total: number;
}

export interface YoYSupplierComparison {
  supplier: string;
  supplier_id: number | null;
  year1_spend: number;
  year2_spend: number;
  change: number;
  change_pct: number;
  year1_transactions: number;
  year2_transactions: number;
}

export interface DetailedYearOverYear {
  summary: YoYSummary;
  monthly_comparison: YoYMonthlyComparison[];
  category_comparison: YoYCategoryComparison[];
  supplier_comparison: YoYSupplierComparison[];
  top_gainers: YoYCategoryComparison[];
  top_decliners: YoYCategoryComparison[];
  available_years: number[];
}

// YoY Category Drilldown types
export interface YoYCategorySupplier {
  name: string;
  supplier_id: number | null;
  year1_spend: number;
  year2_spend: number;
  change: number;
  change_pct: number;
}

export interface YoYMonthlyBreakdown {
  month: string;
  year1_spend: number;
  year2_spend: number;
}

export interface YoYCategoryDrilldown {
  category: string;
  category_id: number;
  year1: string;
  year2: string;
  year1_total: number;
  year2_total: number;
  change_pct: number;
  suppliers: YoYCategorySupplier[];
  monthly_breakdown: YoYMonthlyBreakdown[];
}

// YoY Supplier Drilldown types
export interface YoYSupplierCategory {
  name: string;
  category_id: number | null;
  year1_spend: number;
  year2_spend: number;
  change: number;
  change_pct: number;
}

export interface YoYSupplierDrilldown {
  supplier: string;
  supplier_id: number;
  year1: string;
  year2: string;
  year1_total: number;
  year2_total: number;
  change_pct: number;
  categories: YoYSupplierCategory[];
  monthly_breakdown: YoYMonthlyBreakdown[];
}

export interface ConsolidationSupplier {
  name: string;
  spend: number;
}

export interface ConsolidationOpportunity {
  category: string;
  supplier_count: number;
  total_spend: number;
  suppliers: ConsolidationSupplier[];
  potential_savings: number;
}

// AI Insights types
export type AIInsightType =
  | "cost_optimization"
  | "risk"
  | "anomaly"
  | "consolidation";
export type AIInsightSeverity = "high" | "medium" | "low";

export interface AIInsight {
  id: string;
  type: AIInsightType;
  severity: AIInsightSeverity;
  confidence: number;
  title: string;
  description: string;
  potential_savings: number;
  affected_entities: string[];
  recommended_actions: string[];
  data?: Record<string, unknown>;
  created_at: string;
}

export interface AIInsightsSummary {
  total_insights: number;
  high_priority: number;
  total_potential_savings: number;
  by_type: Record<AIInsightType, number>;
}

/**
 * Tri-state status for AI enhancement availability (Finding #9, CLAUDE.md
 * Cross-Module Open). The orchestrator always emits this so the UI can
 * distinguish "no key configured" from "key configured but LLM call failed".
 *
 * - `enhanced`: LLM enhancement succeeded; `ai_enhancement` payload present.
 * - `unavailable_no_key`: no API key configured; `ai_enhancement` omitted.
 * - `unavailable_failed`: key configured but LLM call failed or returned no
 *    usable result; `ai_enhancement` omitted, `enhancement_error_code` may
 *    be set.
 */
export type AIEnhancementStatus =
  | "enhanced"
  | "unavailable_no_key"
  | "unavailable_failed";

export interface AIInsightsResponse {
  insights: AIInsight[];
  summary: AIInsightsSummary;
  ai_enhancement?: AIEnhancement;
  cache_hit?: boolean;
  enhancement_status?: AIEnhancementStatus;
  enhancement_error_code?: string;
}

export interface AIInsightsListResponse {
  insights: AIInsight[];
  count: number;
  sensitivity?: number;
}

// Structured AI Enhancement types (from tool calling)
export type AIImpactLevel = "high" | "medium" | "low";
export type AIEffortLevel = "low" | "medium" | "high";
export type AIRiskLevel = "critical" | "high" | "moderate" | "low";

export interface AIRecommendation {
  action: string;
  impact: AIImpactLevel;
  effort: AIEffortLevel;
  savings_estimate?: number;
  timeframe?: string;
  affected_insight_ids?: string[];
}

export interface AIRiskAssessment {
  overall_risk_level: AIRiskLevel;
  key_risks?: string[];
  mitigation_steps?: string[];
}

export interface AIQuickWin {
  action: string;
  expected_benefit: string;
}

export interface AIEnhancement {
  priority_actions: AIRecommendation[];
  risk_assessment?: AIRiskAssessment;
  quick_wins?: AIQuickWin[];
  strategic_summary: string;
  provider: "anthropic" | "openai";
  generated_at: string;
}

// Per-Insight AI Enhancement (from Haiku/GPT-4o-mini)
export interface PerInsightEnhancement {
  analysis: string;
  implementation_steps: string[];
  risk_factors: string[];
  confidence_rationale: string;
  timeline_recommendation: string;
}

// AI Insight Feedback types (ROI tracking)
export type InsightActionTaken =
  | "implemented"
  | "dismissed"
  | "deferred"
  | "investigating"
  | "partial";
export type InsightOutcome =
  | "pending"
  | "success"
  | "partial_success"
  | "no_change"
  | "failed";

export interface InsightFeedbackRequest {
  insight_id: string;
  insight_type: AIInsightType;
  insight_title: string;
  insight_severity: AIInsightSeverity;
  predicted_savings?: number;
  action_taken: InsightActionTaken;
  action_notes?: string;
}

export interface InsightFeedbackResponse {
  id: string;
  insight_id: string;
  insight_type: AIInsightType;
  insight_title: string;
  action_taken: InsightActionTaken;
  action_date: string;
  outcome: InsightOutcome;
  message: string;
}

export interface InsightOutcomeUpdateRequest {
  outcome: InsightOutcome;
  actual_savings?: number;
  outcome_notes?: string;
}

export interface InsightOutcomeResponse {
  id: string;
  insight_id: string;
  insight_type: AIInsightType;
  action_taken: InsightActionTaken;
  outcome: InsightOutcome;
  outcome_date: string | null;
  predicted_savings: number | null;
  actual_savings: number | null;
  savings_accuracy: number | null;
  savings_variance: number | null;
  message: string;
}

export interface InsightFeedbackItem {
  id: string;
  insight_id: string;
  insight_type: AIInsightType;
  insight_title: string;
  insight_severity: AIInsightSeverity;
  predicted_savings: number | null;
  action_taken: InsightActionTaken;
  action_date: string;
  action_by: string | null;
  action_notes: string;
  outcome: InsightOutcome;
  actual_savings: number | null;
  outcome_date: string | null;
  outcome_notes: string;
  savings_accuracy: number | null;
  savings_variance: number | null;
}

export interface InsightFeedbackListResponse {
  feedback: InsightFeedbackItem[];
  count: number;
  total: number;
  limit: number;
  offset: number;
}

export interface InsightEffectivenessMetrics {
  total_feedback: number;
  action_breakdown: { action_taken: InsightActionTaken; count: number }[];
  outcome_breakdown: { outcome: InsightOutcome; count: number }[];
  type_breakdown: {
    insight_type: AIInsightType;
    count: number;
    total_predicted: number;
    total_actual: number;
  }[];
  savings_metrics: {
    total_predicted_savings: number;
    total_actual_savings: number;
    avg_predicted_savings: number;
    avg_actual_savings: number;
    implemented_insights: number;
    roi_accuracy_percent: number | null;
    savings_variance: number;
  };
  implementation_success_rate: number;
  successful_implementations: number;
  total_implemented: number;
}

// Async AI Enhancement types
export type AsyncEnhancementStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "not_found";

export interface AsyncEnhancementRequest {
  insights: AIInsight[];
}

export interface AsyncEnhancementRequestResponse {
  task_id: string;
  status: "queued";
  message: string;
}

export interface AsyncEnhancementStatusResponse {
  status: AsyncEnhancementStatus;
  progress: number;
  enhancement?: AIEnhancement;
  error?: string;
  message?: string;
}

// Deep Analysis types
export interface DeepAnalysisRequest {
  insight: AIInsight;
}

export interface DeepAnalysisRequestResponse {
  task_id: string;
  insight_id: string;
  status: "queued";
  message: string;
}

export interface DeepAnalysisRootCause {
  primary_cause: string;
  contributing_factors?: string[];
  systemic_issues?: string[];
}

export interface DeepAnalysisPhase {
  phase: number;
  title: string;
  duration?: string;
  tasks: string[];
  dependencies?: string[];
  deliverables?: string[];
}

export interface DeepAnalysisSavingsBreakdown {
  category: string;
  amount: number;
  description?: string;
}

export interface DeepAnalysisFinancialImpact {
  estimated_savings?: number;
  implementation_cost?: number;
  payback_period?: string;
  roi_percentage?: number;
  savings_breakdown?: DeepAnalysisSavingsBreakdown[];
}

export interface DeepAnalysisRiskFactor {
  risk: string;
  likelihood: "high" | "medium" | "low";
  impact: "high" | "medium" | "low";
  mitigation: string;
}

export interface DeepAnalysisSuccessMetric {
  metric: string;
  target: string;
  measurement_method?: string;
}

export interface DeepAnalysisStakeholder {
  role: string;
  responsibility: string;
}

export interface DeepAnalysisIndustryContext {
  benchmark?: string;
  best_practices?: string[];
}

export interface DeepAnalysis {
  insight_id: string;
  executive_summary: string;
  root_cause_analysis: DeepAnalysisRootCause;
  implementation_roadmap: DeepAnalysisPhase[];
  financial_impact: DeepAnalysisFinancialImpact;
  risk_factors?: DeepAnalysisRiskFactor[];
  success_metrics?: DeepAnalysisSuccessMetric[];
  stakeholders?: DeepAnalysisStakeholder[];
  industry_context?: DeepAnalysisIndustryContext;
  next_steps: string[];
  provider: "anthropic" | "openai";
  model: string;
  generated_at: string;
}

export type DeepAnalysisStatus =
  | "processing"
  | "completed"
  | "failed"
  | "not_found";

export interface DeepAnalysisStatusResponse {
  status: DeepAnalysisStatus;
  progress: number;
  insight_id: string;
  analysis?: DeepAnalysis;
  error?: string;
  message?: string;
}

// LLM Usage & Cost Tracking types
export interface LLMUsageByType {
  request_type: string;
  count: number;
  cost: number;
  tokens: number;
}

export interface LLMUsageByProvider {
  provider: string;
  count: number;
  cost: number;
}

export interface LLMUsageSummary {
  organization_id: number;
  organization_name: string;
  period_days: number;
  total_requests: number;
  total_cost_usd: number;
  total_tokens: number;
  avg_latency_ms: number;
  cache_hit_rate: number;
  prompt_cache_tokens_saved: number;
  by_request_type: LLMUsageByType[];
  by_provider: LLMUsageByProvider[];
}

export interface LLMUsageDailyEntry {
  date: string;
  requests: number;
  cost: number;
  input_tokens: number;
  output_tokens: number;
  cache_reads: number;
}

export interface LLMUsageDailyResponse {
  organization_id: number;
  period_days: number;
  daily_usage: LLMUsageDailyEntry[];
}

// Predictive Analytics types
export type TrendDirection = "increasing" | "decreasing" | "stable";

export interface ForecastPoint {
  month: string;
  predicted_spend: number;
  lower_bound_80: number;
  upper_bound_80: number;
  lower_bound_95: number;
  upper_bound_95: number;
}

export interface TrendInfo {
  direction: TrendDirection;
  monthly_change_rate: number;
  seasonality_detected?: boolean;
  peak_months?: string[];
}

export interface ModelAccuracy {
  mape: number | null;
  data_points_used: number;
  r_squared?: number | null;
}

export interface SpendingForecastResponse {
  forecast: ForecastPoint[];
  trend: TrendInfo;
  model_accuracy: ModelAccuracy;
}

export interface CategoryForecastResponse extends SpendingForecastResponse {
  category_id: number;
}

export interface SupplierForecastResponse extends SpendingForecastResponse {
  supplier_id: number;
}

export interface CategoryTrend {
  category_id: number;
  category_name: string;
  direction: TrendDirection;
  change_rate: number;
}

export interface SupplierTrend {
  supplier_id: number;
  supplier_name: string;
  direction: TrendDirection;
  change_rate: number;
}

export interface GrowthMetrics {
  yoy_growth?: number;
  six_month_growth?: number;
  three_month_growth?: number;
}

export interface TrendAnalysisResponse {
  overall_trend: {
    direction: TrendDirection;
    change_rate: number;
    r_squared: number;
  };
  category_trends: CategoryTrend[];
  supplier_trends: SupplierTrend[];
  growth_metrics: GrowthMetrics;
}

export interface BudgetProjectionResponse {
  annual_budget: number;
  monthly_budget: number;
  ytd_spend: number;
  ytd_budget: number;
  variance: number;
  variance_percentage: number;
  projected_year_end: number;
  projected_variance: number;
  months_elapsed: number;
  months_remaining: number;
  status: "under_budget" | "over_budget" | "on_track" | "no_data";
  monthly_forecast: ForecastPoint[];
}

// Contract Analytics types
export type ContractStatus =
  | "draft"
  | "active"
  | "expiring"
  | "expired"
  | "renewed"
  | "terminated";

export interface Contract {
  id: number;
  uuid: string;
  contract_number: string;
  title: string;
  supplier_id: number;
  supplier_name: string;
  total_value: number;
  annual_value: number | null;
  start_date: string;
  end_date: string;
  renewal_notice_days: number;
  status: ContractStatus;
  auto_renew: boolean;
  categories: string[];
  days_until_expiry: number;
  created_at: string;
  updated_at: string;
}

export interface ContractOverview {
  total_contracts: number;
  active_contracts: number;
  total_value: number;
  annual_value: number;
  expiring_soon: number;
  expired: number;
  coverage_percentage: number;
  total_contracted_spend: number;
  off_contract_spend: number;
}

export interface ContractListItem {
  id: number;
  uuid: string;
  contract_number: string;
  title: string;
  supplier_name: string;
  total_value: number;
  status: ContractStatus;
  start_date: string;
  end_date: string;
  days_until_expiry: number;
  utilization_percentage: number;
}

export interface ContractDetail extends Contract {
  actual_spend: number;
  utilization_percentage: number;
  monthly_spend: { month: string; amount: number }[];
  category_breakdown: { category: string; amount: number }[];
  remaining_value: number;
  average_monthly_spend: number;
}

export interface ExpiringContract {
  id: number;
  contract_number: string;
  title: string;
  supplier_name: string;
  end_date: string;
  days_until_expiry: number;
  total_value: number;
  actual_spend: number;
  utilization_percentage: number;
  renewal_notice_days: number;
  auto_renew: boolean;
  recommendation: "renew" | "renegotiate" | "terminate" | "review";
  recommendation_reason: string;
}

export interface ContractPerformance {
  contract_id: number;
  contract_number: string;
  title: string;
  total_value: number;
  actual_spend: number;
  utilization_percentage: number;
  remaining_value: number;
  monthly_trend: { month: string; amount: number; cumulative: number }[];
  supplier_performance: {
    on_time_delivery_rate: number;
    quality_score: number;
    transaction_count: number;
  };
  run_rate: number;
  projected_spend: number;
  variance_at_expiry: number;
}

export interface ContractSavingsOpportunity {
  type: "underutilized" | "off_contract" | "consolidation" | "price_variance";
  title: string;
  description: string;
  potential_savings: number;
  affected_contracts?: number[];
  affected_suppliers?: string[];
  affected_categories?: string[];
  confidence: number;
  recommended_action: string;
}

export interface ContractSavingsResponse {
  opportunities: ContractSavingsOpportunity[];
  total_potential_savings: number;
  opportunity_count: number;
}

export interface RenewalRecommendation {
  contract_id: number;
  contract_number: string;
  title: string;
  supplier_name: string;
  end_date: string;
  days_until_expiry: number;
  total_value: number;
  actual_spend: number;
  utilization_percentage: number;
  recommendation: "renew" | "renegotiate" | "terminate" | "review";
  recommendation_reason: string;
  suggested_new_value: number | null;
  priority: "high" | "medium" | "low";
}

export interface ContractVsActualItem {
  contract_id: number;
  contract_number: string;
  title: string;
  contracted_value: number;
  actual_spend: number;
  variance: number;
  variance_percentage: number;
  status: "over" | "under" | "on_track";
}

export interface ContractVsActualResponse {
  contracts: ContractVsActualItem[];
  summary: {
    total_contracted: number;
    total_actual: number;
    total_variance: number;
    overall_utilization: number;
  };
  monthly_comparison?: { month: string; contracted: number; actual: number }[];
}

// Compliance types
export type ViolationType =
  | "amount_exceeded"
  | "non_preferred_supplier"
  | "restricted_category"
  | "no_contract"
  | "approval_missing";
export type ViolationSeverity = "critical" | "high" | "medium" | "low";
export type RiskLevel = "high" | "medium" | "low";

export interface ComplianceOverview {
  total_transactions: number;
  total_spend: number;
  compliance_rate: number;
  total_violations: number;
  unresolved_violations: number;
  resolved_today: number;
  severity_breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  maverick_spend: number;
  maverick_percentage: number;
  on_contract_spend: number;
  active_policies: number;
}

export interface MaverickSupplier {
  supplier_id: number;
  supplier_name: string;
  spend: number;
  transaction_count: number;
}

export interface MaverickCategory {
  category_id: number;
  category_name: string;
  spend: number;
  transaction_count: number;
}

export interface MaverickRecommendation {
  type: "contract_negotiation" | "category_coverage" | "spend_consolidation";
  title: string;
  description: string;
  potential_savings: number;
  affected_suppliers?: string[];
  affected_categories?: string[];
  priority: "high" | "medium" | "low";
}

export interface MaverickSpendAnalysis {
  total_maverick_spend: number;
  total_on_contract_spend: number;
  maverick_percentage: number;
  maverick_suppliers: MaverickSupplier[];
  maverick_supplier_count: number;
  maverick_categories: MaverickCategory[];
  on_contract_suppliers: MaverickSupplier[];
  recommendations: MaverickRecommendation[];
}

export interface PolicyViolation {
  id: number;
  uuid: string;
  transaction_id: number;
  transaction_date: string;
  transaction_amount: number;
  supplier_name: string;
  category_name: string;
  policy_name: string;
  violation_type: ViolationType;
  violation_type_display: string;
  severity: ViolationSeverity;
  details: Record<string, unknown>;
  is_resolved: boolean;
  resolved_at: string | null;
  resolution_notes: string;
  created_at: string;
}

export interface ViolationTrendMonth {
  month: string;
  total: number;
  resolved: number;
  resolution_rate: number;
  critical: number;
  high: number;
}

export interface ViolationTrends {
  monthly_trend: ViolationTrendMonth[];
  by_type: {
    amount_exceeded: number;
    non_preferred_supplier: number;
    restricted_category: number;
    no_contract: number;
    approval_missing: number;
  };
}

export interface SupplierComplianceScore {
  supplier_id: number;
  supplier_name: string;
  compliance_score: number;
  transaction_count: number;
  violation_count: number;
  unresolved_violations: number;
  has_contract: boolean;
  total_spend: number;
  risk_level: RiskLevel;
}

export interface SpendingPolicy {
  id: number;
  uuid: string;
  name: string;
  description: string;
  is_active: boolean;
  rules_summary: string[];
  violation_count: number;
  created_at: string;
}

// Report Types
export type ReportType =
  | "spend_analysis"
  | "supplier_performance"
  | "savings_opportunities"
  | "price_trends"
  | "contract_compliance"
  | "executive_summary"
  | "pareto_analysis"
  | "stratification"
  | "seasonality"
  | "year_over_year"
  | "tail_spend"
  | "custom"
  // P2P Report Types
  | "p2p_pr_status"
  | "p2p_po_compliance"
  | "p2p_ap_aging";

export type ReportFormat = "pdf" | "xlsx" | "csv";

export type ReportStatus =
  | "draft"
  | "generating"
  | "completed"
  | "failed"
  | "scheduled";

export type ScheduleFrequency =
  | "daily"
  | "weekly"
  | "bi_weekly"
  | "monthly"
  | "quarterly";

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  report_type: ReportType;
  icon?: string;
  default_parameters?: Record<string, unknown>;
}

export interface ReportListItem {
  id: string;
  name: string;
  description: string;
  report_type: ReportType;
  report_type_display: string;
  report_format: ReportFormat;
  report_format_display: string;
  status: ReportStatus;
  status_display: string;
  period_start: string | null;
  period_end: string | null;
  created_by_name: string;
  created_at: string;
  generated_at: string | null;
  is_expired: boolean;
  file_size: number | null;
  is_scheduled: boolean;
  schedule_frequency: ScheduleFrequency | "";
  next_run: string | null;
}

export interface ReportDetail extends ReportListItem {
  organization_name: string;
  filters: Record<string, unknown>;
  parameters: Record<string, unknown>;
  error_message: string;
  file_path: string;
  summary_data: Record<string, unknown>;
  is_public: boolean;
  shared_with_users: string[];
  schedule_frequency_display: string;
  last_run: string | null;
  updated_at: string;
}

export interface ReportGenerateRequest {
  report_type: ReportType;
  report_format?: ReportFormat;
  name?: string;
  description?: string;
  period_start?: string;
  period_end?: string;
  filters?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  async_generation?: boolean;
}

export interface ReportGenerateResponse {
  id: string;
  status: ReportStatus;
  message?: string;
}

// Report Preview Data (from preview endpoint)
export interface ReportPreviewData {
  metadata?: {
    report_type?: string;
    report_title?: string;
    organization?: string;
    period_start?: string;
    period_end?: string;
    generated_at?: string;
    filters_applied?: Record<string, unknown>;
  };
  overview?: {
    total_spend?: number;
    transaction_count?: number;
    supplier_count?: number;
    category_count?: number;
    avg_transaction?: number;
  };
  spend_by_category?: Array<{
    category: string;
    amount: number;
    count: number;
    percentage?: number;
  }>;
  spend_by_supplier?: Array<{
    supplier: string;
    amount: number;
    count: number;
    percentage?: number;
  }>;
  // Preview metadata
  _preview?: boolean;
  _truncated?: boolean;
  // Allow additional fields from different report types
  [key: string]: unknown;
}

export interface ReportScheduleRequest {
  name: string;
  report_type: ReportType;
  report_format?: ReportFormat;
  period_start?: string;
  period_end?: string;
  filters?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  is_scheduled: boolean;
  schedule_frequency: ScheduleFrequency;
}

export interface ReportShareRequest {
  user_ids?: number[];
  is_public?: boolean;
}

export interface ReportStatusResponse {
  id: string;
  status: ReportStatus;
  error_message: string;
  generated_at: string | null;
  file_size: number | null;
}

export interface ReportListResponse {
  results: ReportListItem[];
  total: number;
  limit: number;
  offset: number;
}

// Paginated response
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Query parameters
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface SupplierQueryParams extends PaginationParams {
  search?: string;
  is_active?: boolean;
  ordering?: string;
}

export interface CategoryQueryParams extends PaginationParams {
  search?: string;
  is_active?: boolean;
  parent?: number | null;
  ordering?: string;
}

export interface TransactionQueryParams extends PaginationParams {
  search?: string;
  supplier?: number;
  category?: number;
  start_date?: string;
  end_date?: string;
  fiscal_year?: number;
  ordering?: string;
}

export interface ExportParams {
  start_date?: string;
  end_date?: string;
  supplier?: number;
  category?: number;
}

// =====================
// API Configuration
// =====================

// API base URL
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Create axios instance with credentials for HTTP-only cookie auth
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Send HTTP-only cookies with requests
});

// Response interceptor to handle token refresh via cookies
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token via cookie
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Refresh token is in HTTP-only cookie, server will read it
        await axios.post(
          `${API_BASE_URL}/auth/token/refresh/`,
          {},
          {
            withCredentials: true,
          },
        );

        // Retry original request - new access token is in cookie
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear user data and redirect to login
        localStorage.removeItem("user");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

// =====================
// API Functions
// =====================

// Organization param storage key (used by OrganizationContext)
const ORG_STORAGE_KEY = "active_organization_id";

/**
 * Get organization_id parameter for API calls.
 * Returns empty object if viewing user's own org (default behavior).
 */
export function getOrganizationParam(): { organization_id?: number } {
  const stored = localStorage.getItem(ORG_STORAGE_KEY);
  return stored ? { organization_id: parseInt(stored, 10) } : {};
}

// Authentication API
// Note: JWT tokens are managed via HTTP-only cookies for XSS protection
export const authAPI = {
  register: (data: RegisterRequest): Promise<AxiosResponse<AuthResponse>> =>
    api.post("/auth/register/", data),

  login: (data: LoginRequest): Promise<AxiosResponse<AuthResponse>> =>
    api.post("/auth/login/", data),

  // Logout clears HTTP-only cookies on the server side
  logout: (): Promise<AxiosResponse<{ message: string }>> =>
    api.post("/auth/logout/"),

  getCurrentUser: (): Promise<AxiosResponse<User>> => api.get("/auth/user/"),

  changePassword: (
    data: ChangePasswordRequest,
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post("/auth/change-password/", data),

  // Refresh token endpoint - tokens in HTTP-only cookies
  refreshToken: (): Promise<AxiosResponse<{ message: string }>> =>
    api.post("/auth/token/refresh/"),

  // User Preferences
  getPreferences: (): Promise<AxiosResponse<UserPreferences>> =>
    api.get("/auth/preferences/"),

  updatePreferences: (
    data: Partial<UserPreferences>,
  ): Promise<AxiosResponse<UserPreferences>> =>
    api.patch("/auth/preferences/", data),

  replacePreferences: (
    data: UserPreferences,
  ): Promise<AxiosResponse<UserPreferences>> =>
    api.put("/auth/preferences/", data),

  // Organizations (superusers get all, others get their own)
  getOrganizations: (): Promise<
    AxiosResponse<PaginatedResponse<Organization>>
  > => api.get("/auth/organizations/"),

  getOrganization: (id: number): Promise<AxiosResponse<Organization>> =>
    api.get(`/auth/organizations/${id}/`),

  // User Organization Memberships (multi-org support)
  getUserOrganizations: (): Promise<
    AxiosResponse<{ organizations: OrganizationMembership[]; count: number }>
  > => api.get("/auth/user/organizations/"),

  switchOrganization: (
    orgId: number,
  ): Promise<AxiosResponse<{ message: string; organization_id: number }>> =>
    api.post(`/auth/user/organizations/${orgId}/switch/`),

  // Organization Savings Configuration (Admin only)
  getSavingsConfig: (
    orgId: number,
  ): Promise<AxiosResponse<SavingsConfigResponse>> =>
    api.get(`/auth/organizations/${orgId}/savings-config/`),

  updateSavingsConfig: (
    orgId: number,
    data: Partial<SavingsConfig>,
  ): Promise<AxiosResponse<{ savings_config: SavingsConfig }>> =>
    api.patch(`/auth/organizations/${orgId}/savings-config/`, data),

  exportSavingsConfigPdf: (orgId: number): Promise<AxiosResponse<Blob>> =>
    api.get(`/auth/organizations/${orgId}/savings-config/export/`, {
      responseType: "blob",
    }),
};

// Procurement API
// Read endpoints support organization_id param for superuser org switching
export const procurementAPI = {
  // Suppliers
  getSuppliers: (
    params?: SupplierQueryParams,
  ): Promise<AxiosResponse<PaginatedResponse<Supplier>>> =>
    api.get("/procurement/suppliers/", {
      params: { ...params, ...getOrganizationParam() },
    }),

  getSupplier: (id: number): Promise<AxiosResponse<Supplier>> =>
    api.get(`/procurement/suppliers/${id}/`, {
      params: getOrganizationParam(),
    }),

  createSupplier: (
    data: SupplierCreateRequest,
  ): Promise<AxiosResponse<Supplier>> =>
    api.post("/procurement/suppliers/", data),

  updateSupplier: (
    id: number,
    data: SupplierUpdateRequest,
  ): Promise<AxiosResponse<Supplier>> =>
    api.patch(`/procurement/suppliers/${id}/`, data),

  deleteSupplier: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/procurement/suppliers/${id}/`),

  // Categories
  getCategories: (
    params?: CategoryQueryParams,
  ): Promise<AxiosResponse<PaginatedResponse<Category>>> =>
    api.get("/procurement/categories/", {
      params: { ...params, ...getOrganizationParam() },
    }),

  getCategory: (id: number): Promise<AxiosResponse<Category>> =>
    api.get(`/procurement/categories/${id}/`, {
      params: getOrganizationParam(),
    }),

  createCategory: (
    data: CategoryCreateRequest,
  ): Promise<AxiosResponse<Category>> =>
    api.post("/procurement/categories/", data),

  updateCategory: (
    id: number,
    data: CategoryUpdateRequest,
  ): Promise<AxiosResponse<Category>> =>
    api.patch(`/procurement/categories/${id}/`, data),

  deleteCategory: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/procurement/categories/${id}/`),

  // Transactions
  getTransactions: (
    params?: TransactionQueryParams,
  ): Promise<AxiosResponse<PaginatedResponse<Transaction>>> =>
    api.get("/procurement/transactions/", {
      params: { ...params, ...getOrganizationParam() },
    }),

  getTransaction: (id: number): Promise<AxiosResponse<Transaction>> =>
    api.get(`/procurement/transactions/${id}/`, {
      params: getOrganizationParam(),
    }),

  createTransaction: (
    data: TransactionCreateRequest,
  ): Promise<AxiosResponse<Transaction>> =>
    api.post("/procurement/transactions/", data),

  updateTransaction: (
    id: number,
    data: TransactionUpdateRequest,
  ): Promise<AxiosResponse<Transaction>> =>
    api.patch(`/procurement/transactions/${id}/`, data),

  deleteTransaction: (id: number): Promise<AxiosResponse<void>> =>
    api.delete(`/procurement/transactions/${id}/`),

  uploadCSV: (
    file: File,
    skipDuplicates: boolean = true,
  ): Promise<AxiosResponse<CSVUploadResponse>> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("skip_duplicates", String(skipDuplicates));
    return api.post("/procurement/transactions/upload_csv/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  bulkDelete: (ids: number[]): Promise<AxiosResponse<BulkDeleteResponse>> =>
    api.post("/procurement/transactions/bulk_delete/", { ids }),

  exportCSV: (params?: ExportParams): Promise<AxiosResponse<Blob>> =>
    api.get("/procurement/transactions/export/", {
      params: { ...params, ...getOrganizationParam() },
      responseType: "blob",
    }),

  // Uploads
  getUploads: (
    params?: PaginationParams,
  ): Promise<AxiosResponse<PaginatedResponse<DataUpload>>> =>
    api.get("/procurement/uploads/", {
      params: { ...params, ...getOrganizationParam() },
    }),
};

// Analytics API
// All endpoints support organization_id param for superuser org switching
// All endpoints support filter params: date_from, date_to, supplier_ids, category_ids, min_amount, max_amount
export const analyticsAPI = {
  getOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<OverviewStats>> =>
    api.get("/analytics/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSpendByCategory: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SpendByCategory[]>> =>
    api.get("/analytics/spend-by-category/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getCategoryDetails: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<CategoryDetail[]>> =>
    api.get("/analytics/categories/detailed/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSpendBySupplier: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SpendBySupplier[]>> =>
    api.get("/analytics/spend-by-supplier/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSupplierDetails: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierAnalysis>> =>
    api.get("/analytics/suppliers/detailed/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getMonthlyTrend: (
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<MonthlyTrend[]>> =>
    api.get("/analytics/monthly-trend/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getParetoAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ParetoItem[]>> =>
    api.get("/analytics/pareto/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSupplierDrilldown: (
    supplierId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierDrilldown>> =>
    api.get(`/analytics/pareto/supplier/${supplierId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getCategoryDrilldown: (
    categoryId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<CategoryDrilldown>> =>
    api.get(`/analytics/category/${categoryId}/drilldown/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getTailSpend: (
    threshold: number = 20,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<TailSpendAnalysis>> =>
    api.get("/analytics/tail-spend/", {
      params: {
        threshold,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getDetailedTailSpend: (
    threshold: number = 50000,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<DetailedTailSpend>> =>
    api.get("/analytics/tail-spend/detailed/", {
      params: {
        threshold,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getTailSpendCategoryDrilldown: (
    categoryId: number,
    threshold: number = 50000,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<TailSpendCategoryDrilldown>> =>
    api.get(`/analytics/tail-spend/category/${categoryId}/`, {
      params: {
        threshold,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getTailSpendVendorDrilldown: (
    supplierId: number,
    threshold: number = 50000,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<TailSpendVendorDrilldown>> =>
    api.get(`/analytics/tail-spend/vendor/${supplierId}/`, {
      params: {
        threshold,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getStratification: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SpendStratification>> =>
    api.get("/analytics/stratification/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getDetailedStratification: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<DetailedStratification>> =>
    api.get("/analytics/stratification/detailed/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSegmentDrilldown: (
    segmentName: string,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SegmentDrilldown>> =>
    api.get(`/analytics/stratification/segment/${segmentName}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getBandDrilldown: (
    bandName: string,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<BandDrilldown>> =>
    api.get(`/analytics/stratification/band/${encodeURIComponent(bandName)}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSeasonality: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SeasonalityData[]>> =>
    api.get("/analytics/seasonality/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getDetailedSeasonality: (
    useFiscalYear: boolean = true,
    filters?: AnalyticsFilters,
    year?: number,
  ): Promise<AxiosResponse<DetailedSeasonality>> =>
    api.get("/analytics/seasonality/detailed/", {
      params: {
        ...getOrganizationParam(),
        use_fiscal_year: useFiscalYear,
        ...(year !== undefined ? { year } : {}),
        ...buildFilterParams(filters),
      },
    }),

  getSeasonalityCategoryDrilldown: (
    categoryId: number,
    useFiscalYear: boolean = true,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SeasonalityCategoryDrilldown>> =>
    api.get(`/analytics/seasonality/category/${categoryId}/`, {
      params: {
        ...getOrganizationParam(),
        use_fiscal_year: useFiscalYear,
        ...buildFilterParams(filters),
      },
    }),

  getYearOverYear: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<YearOverYearData[]>> =>
    api.get("/analytics/year-over-year/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getDetailedYearOverYear: (
    useFiscalYear: boolean = true,
    year1?: number,
    year2?: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<DetailedYearOverYear>> =>
    api.get("/analytics/year-over-year/detailed/", {
      params: {
        ...getOrganizationParam(),
        use_fiscal_year: useFiscalYear,
        year1,
        year2,
        ...buildFilterParams(filters),
      },
    }),

  getYoYCategoryDrilldown: (
    categoryId: number,
    useFiscalYear: boolean = true,
    year1?: number,
    year2?: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<YoYCategoryDrilldown>> =>
    api.get(`/analytics/year-over-year/category/${categoryId}/`, {
      params: {
        ...getOrganizationParam(),
        use_fiscal_year: useFiscalYear,
        year1,
        year2,
        ...buildFilterParams(filters),
      },
    }),

  getYoYSupplierDrilldown: (
    supplierId: number,
    useFiscalYear: boolean = true,
    year1?: number,
    year2?: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<YoYSupplierDrilldown>> =>
    api.get(`/analytics/year-over-year/supplier/${supplierId}/`, {
      params: {
        ...getOrganizationParam(),
        use_fiscal_year: useFiscalYear,
        year1,
        year2,
        ...buildFilterParams(filters),
      },
    }),

  getConsolidation: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ConsolidationOpportunity[]>> =>
    api.get("/analytics/consolidation/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  // AI Insights endpoints
  getAIInsights: (
    refresh: boolean = false,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AIInsightsResponse>> =>
    api.get("/analytics/ai-insights/", {
      params: {
        refresh: refresh ? "true" : undefined,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getAIInsightsCost: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AIInsightsListResponse>> =>
    api.get("/analytics/ai-insights/cost/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getAIInsightsRisk: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AIInsightsListResponse>> =>
    api.get("/analytics/ai-insights/risk/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getAIInsightsAnomalies: (
    sensitivity: number = 2.0,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AIInsightsListResponse>> =>
    api.get("/analytics/ai-insights/anomalies/", {
      params: {
        sensitivity,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  // AI Insight Feedback endpoints (ROI tracking)
  recordInsightFeedback: (
    data: InsightFeedbackRequest,
  ): Promise<AxiosResponse<InsightFeedbackResponse>> =>
    api.post("/analytics/ai-insights/feedback/", data, {
      params: getOrganizationParam(),
    }),

  updateInsightOutcome: (
    feedbackId: string,
    data: InsightOutcomeUpdateRequest,
  ): Promise<AxiosResponse<InsightOutcomeResponse>> =>
    api.patch(`/analytics/ai-insights/feedback/${feedbackId}/`, data, {
      params: getOrganizationParam(),
    }),

  getInsightEffectiveness: (): Promise<
    AxiosResponse<InsightEffectivenessMetrics>
  > =>
    api.get("/analytics/ai-insights/feedback/effectiveness/", {
      params: getOrganizationParam(),
    }),

  listInsightFeedback: (params?: {
    insight_type?: AIInsightType;
    action_taken?: InsightActionTaken;
    outcome?: InsightOutcome;
    limit?: number;
    offset?: number;
  }): Promise<AxiosResponse<InsightFeedbackListResponse>> =>
    api.get("/analytics/ai-insights/feedback/list/", {
      params: { ...params, ...getOrganizationParam() },
    }),

  deleteInsightFeedback: (feedbackId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/analytics/ai-insights/feedback/${feedbackId}/delete/`, {
      params: getOrganizationParam(),
    }),

  // Async AI Enhancement endpoints
  requestAsyncEnhancement: (
    data: AsyncEnhancementRequest,
  ): Promise<AxiosResponse<AsyncEnhancementRequestResponse>> =>
    api.post("/analytics/ai-insights/enhance/request/", data, {
      params: getOrganizationParam(),
    }),

  getAsyncEnhancementStatus: (): Promise<
    AxiosResponse<AsyncEnhancementStatusResponse>
  > =>
    api.get("/analytics/ai-insights/enhance/status/", {
      params: getOrganizationParam(),
    }),

  // Deep Analysis endpoints
  requestDeepAnalysis: (
    data: DeepAnalysisRequest,
  ): Promise<AxiosResponse<DeepAnalysisRequestResponse>> =>
    api.post("/analytics/ai-insights/deep-analysis/request/", data, {
      params: getOrganizationParam(),
    }),

  getDeepAnalysisStatus: (
    insightId: string,
  ): Promise<AxiosResponse<DeepAnalysisStatusResponse>> =>
    api.get(`/analytics/ai-insights/deep-analysis/status/${insightId}/`, {
      params: getOrganizationParam(),
    }),

  // LLM Usage & Cost Tracking endpoints
  getLLMUsageSummary: (
    days: number = 30,
  ): Promise<AxiosResponse<LLMUsageSummary>> =>
    api.get("/analytics/ai-insights/usage/", {
      params: { days, ...getOrganizationParam() },
    }),

  getLLMUsageDaily: (
    days: number = 30,
  ): Promise<AxiosResponse<LLMUsageDailyResponse>> =>
    api.get("/analytics/ai-insights/usage/daily/", {
      params: { days, ...getOrganizationParam() },
    }),

  // Predictive Analytics endpoints
  getSpendingForecast: (
    months: number = 6,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SpendingForecastResponse>> =>
    api.get("/analytics/predictions/spending/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getCategoryForecast: (
    categoryId: number,
    months: number = 6,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<CategoryForecastResponse>> =>
    api.get(`/analytics/predictions/category/${categoryId}/`, {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getSupplierForecast: (
    supplierId: number,
    months: number = 6,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierForecastResponse>> =>
    api.get(`/analytics/predictions/supplier/${supplierId}/`, {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getTrendAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<TrendAnalysisResponse>> =>
    api.get("/analytics/predictions/trends/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getBudgetProjection: (
    annualBudget: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<BudgetProjectionResponse>> =>
    api.get("/analytics/predictions/budget/", {
      params: {
        annual_budget: annualBudget,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  // Contract Analytics endpoints
  getContractOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ContractOverview>> =>
    api.get("/analytics/contracts/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getContracts: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<{ contracts: ContractListItem[]; count: number }>> =>
    api.get("/analytics/contracts/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getContractDetail: (
    contractId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ContractDetail>> =>
    api.get(`/analytics/contracts/${contractId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getExpiringContracts: (
    days: number = 90,
    filters?: AnalyticsFilters,
  ): Promise<
    AxiosResponse<{
      contracts: ExpiringContract[];
      count: number;
      days_threshold: number;
    }>
  > =>
    api.get("/analytics/contracts/expiring/", {
      params: {
        days,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getContractPerformance: (
    contractId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ContractPerformance>> =>
    api.get(`/analytics/contracts/${contractId}/performance/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getContractSavings: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ContractSavingsResponse>> =>
    api.get("/analytics/contracts/savings/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getContractRenewals: (
    filters?: AnalyticsFilters,
  ): Promise<
    AxiosResponse<{ recommendations: RenewalRecommendation[]; count: number }>
  > =>
    api.get("/analytics/contracts/renewals/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getContractVsActual: (
    contractId?: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ContractVsActualResponse>> =>
    api.get("/analytics/contracts/vs-actual/", {
      params: {
        ...(contractId ? { contract_id: contractId } : {}),
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  // Compliance & Maverick Spend endpoints
  getComplianceOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ComplianceOverview>> =>
    api.get("/analytics/compliance/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getMaverickSpendAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<MaverickSpendAnalysis>> =>
    api.get("/analytics/compliance/maverick-spend/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPolicyViolations: (
    params?: {
      resolved?: boolean;
      severity?: ViolationSeverity;
      limit?: number;
    },
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<{ violations: PolicyViolation[]; count: number }>> =>
    api.get("/analytics/compliance/violations/", {
      params: {
        ...params,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  resolveViolation: (
    violationId: number,
    resolutionNotes: string,
  ): Promise<
    AxiosResponse<{
      id: number;
      is_resolved: boolean;
      resolved_at: string;
      resolution_notes: string;
    }>
  > =>
    api.post(
      `/analytics/compliance/violations/${violationId}/resolve/`,
      { resolution_notes: resolutionNotes },
      { params: getOrganizationParam() },
    ),

  getViolationTrends: (
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ViolationTrends>> =>
    api.get("/analytics/compliance/trends/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getSupplierComplianceScores: (
    filters?: AnalyticsFilters,
  ): Promise<
    AxiosResponse<{ suppliers: SupplierComplianceScore[]; count: number }>
  > =>
    api.get("/analytics/compliance/supplier-scores/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSpendingPolicies: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<{ policies: SpendingPolicy[]; count: number }>> =>
    api.get("/analytics/compliance/policies/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),
};

// Reports API
export const reportsAPI = {
  // Templates
  getTemplates: (): Promise<AxiosResponse<ReportTemplate[]>> =>
    api.get("/reports/templates/", { params: getOrganizationParam() }),

  getTemplate: (templateId: string): Promise<AxiosResponse<ReportTemplate>> =>
    api.get(`/reports/templates/${templateId}/`, {
      params: getOrganizationParam(),
    }),

  // Report Generation
  generate: (
    data: ReportGenerateRequest,
  ): Promise<AxiosResponse<ReportDetail | ReportGenerateResponse>> =>
    api.post("/reports/generate/", data, { params: getOrganizationParam() }),

  // Report Preview (lightweight preview without creating a Report record)
  preview: (
    data: ReportGenerateRequest,
  ): Promise<AxiosResponse<ReportPreviewData>> =>
    api.post("/reports/preview/", data, { params: getOrganizationParam() }),

  // Report List and Detail
  getReports: (params?: {
    status?: ReportStatus;
    report_type?: ReportType;
    limit?: number;
    offset?: number;
  }): Promise<AxiosResponse<ReportListResponse>> =>
    api.get("/reports/", { params: { ...params, ...getOrganizationParam() } }),

  getReport: (reportId: string): Promise<AxiosResponse<ReportDetail>> =>
    api.get(`/reports/${reportId}/`, { params: getOrganizationParam() }),

  getStatus: (reportId: string): Promise<AxiosResponse<ReportStatusResponse>> =>
    api.get(`/reports/${reportId}/status/`, { params: getOrganizationParam() }),

  deleteReport: (reportId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/reports/${reportId}/delete/`, {
      params: getOrganizationParam(),
    }),

  // Download report file
  // NOTE: Use 'output_format' not 'format' to avoid conflict with DRF content negotiation
  download: async (reportId: string, format?: ReportFormat): Promise<Blob> => {
    const response = await api.get(`/reports/${reportId}/download/`, {
      params: { output_format: format, ...getOrganizationParam() },
      responseType: "blob",
    });
    return response.data;
  },

  // Sharing
  share: (
    reportId: string,
    data: ReportShareRequest,
  ): Promise<AxiosResponse<ReportDetail>> =>
    api.post(`/reports/${reportId}/share/`, data, {
      params: getOrganizationParam(),
    }),

  // Scheduled Reports
  getSchedules: (): Promise<AxiosResponse<ReportListItem[]>> =>
    api.get("/reports/schedules/", { params: getOrganizationParam() }),

  createSchedule: (
    data: ReportScheduleRequest,
  ): Promise<AxiosResponse<ReportListItem>> =>
    api.post("/reports/schedules/", data, { params: getOrganizationParam() }),

  getSchedule: (scheduleId: string): Promise<AxiosResponse<ReportDetail>> =>
    api.get(`/reports/schedules/${scheduleId}/`, {
      params: getOrganizationParam(),
    }),

  updateSchedule: (
    scheduleId: string,
    data: Partial<ReportScheduleRequest>,
  ): Promise<AxiosResponse<ReportDetail>> =>
    api.put(`/reports/schedules/${scheduleId}/`, data, {
      params: getOrganizationParam(),
    }),

  deleteSchedule: (scheduleId: string): Promise<AxiosResponse<void>> =>
    api.delete(`/reports/schedules/${scheduleId}/`, {
      params: getOrganizationParam(),
    }),

  runScheduleNow: (
    scheduleId: string,
  ): Promise<AxiosResponse<{ message: string; id: string }>> =>
    api.post(
      `/reports/schedules/${scheduleId}/run-now/`,
      {},
      { params: getOrganizationParam() },
    ),
};

// =====================
// P2P (Procure-to-Pay) Analytics Types
// =====================

// P2P Document Status Types
export type PRStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "converted_to_po"
  | "cancelled";
export type PRPriority = "low" | "normal" | "high" | "urgent";
export type POStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "sent_to_supplier"
  | "acknowledged"
  | "partially_received"
  | "fully_received"
  | "closed"
  | "cancelled";
export type GRStatus = "pending" | "accepted" | "partial_accept" | "rejected";
export type InvoiceStatus =
  | "received"
  | "pending_match"
  | "matched"
  | "exception"
  | "approved"
  | "on_hold"
  | "paid"
  | "disputed";
export type MatchStatus =
  | "unmatched"
  | "2way_matched"
  | "3way_matched"
  | "exception";
export type ExceptionType =
  | "price_variance"
  | "quantity_variance"
  | "no_po"
  | "duplicate"
  | "missing_gr"
  | "other";

// P2P Cycle Overview
export interface P2PCycleStage {
  name: string;
  avg_days: number;
  target_days: number;
  variance_pct: number;
  status: "on_track" | "warning" | "critical";
}

export interface P2PCycleOverview {
  stages: {
    pr_to_po: P2PCycleStage;
    po_to_gr: P2PCycleStage;
    gr_to_invoice: P2PCycleStage;
    invoice_to_payment: P2PCycleStage;
  };
  total_cycle: {
    avg_days: number;
    target_days: number;
    variance_pct: number;
  };
  summary: {
    total_transactions: number;
    on_time_rate: number;
    bottleneck_stage: string;
  };
}

export interface P2PCycleByCategory {
  category: string;
  category_id: number;
  pr_to_po_days: number;
  po_to_gr_days: number;
  gr_to_invoice_days: number;
  invoice_to_payment_days: number;
  total_days: number;
  transaction_count: number;
  total_spend: number;
}

export interface P2PCycleBySupplier {
  supplier: string;
  supplier_id: number;
  pr_to_po_days: number;
  po_to_gr_days: number;
  gr_to_invoice_days: number;
  invoice_to_payment_days: number;
  total_days: number;
  transaction_count: number;
  on_time_rate: number;
}

export interface P2PCycleTrend {
  month: string;
  pr_to_po_days: number;
  po_to_gr_days: number;
  gr_to_invoice_days: number;
  invoice_to_payment_days: number;
  total_days: number;
}

export interface P2PBottleneck {
  stage: string;
  avg_days: number;
  target_days: number;
  variance_pct: number;
  status: "on_track" | "warning" | "critical";
  impact: string;
  recommendations: string[];
}

export interface P2PBottleneckAnalysis {
  bottlenecks: P2PBottleneck[];
  primary_bottleneck: string;
  estimated_savings_days: number;
}

export interface P2PFunnelStage {
  stage: string;
  count: number;
  value: number;
  conversion_rate: number;
}

export interface P2PProcessFunnel {
  stages: P2PFunnelStage[];
  drop_off_points: {
    from: string;
    to: string;
    lost_count: number;
    lost_value: number;
  }[];
}

export interface P2PStageDrilldownItem {
  document_number: string;
  document_type: "PR" | "PO" | "GR" | "Invoice";
  document_id: number;
  supplier: string;
  supplier_name?: string;
  amount: number;
  days_in_stage: number;
  status: string;
  created_date: string;
}

export interface P2PStageDrilldown {
  stage: string;
  avg_days: number;
  documents_count: number;
  total_value: number;
  slowest_documents: P2PStageDrilldownItem[];
}

// 3-Way Matching Types
export interface MatchingOverview {
  total_invoices: number;
  total_amount: number;
  three_way_matched: { count: number; amount: number; percentage: number };
  two_way_matched: { count: number; amount: number; percentage: number };
  exceptions: { count: number; amount: number; percentage: number };
  avg_resolution_days: number;
}

export interface InvoiceException {
  invoice_id: number;
  invoice_number: string;
  supplier: string;
  supplier_id: number;
  invoice_amount: number;
  exception_type: ExceptionType;
  exception_amount: number | null;
  days_open: number;
  po_number: string | null;
  invoice_date: string;
  status: InvoiceStatus;
  exception_notes: string;
}

export interface ExceptionsByType {
  exception_type: ExceptionType;
  count: number;
  amount: number;
  percentage: number;
}

export interface ExceptionsBySupplier {
  supplier: string;
  supplier_id: number;
  total_invoices: number;
  exception_count: number;
  exception_rate: number;
  exception_amount: number;
  primary_exception_type: ExceptionType | null;
}

export interface PriceVarianceItem {
  invoice_id: number;
  invoice_number: string;
  supplier: string;
  po_number: string;
  po_price: number;
  invoice_price: number;
  variance_amount: number;
  variance_pct: number;
}

export interface PriceVarianceAnalysis {
  total_variance: number;
  variance_count: number;
  avg_variance_pct: number;
  items: PriceVarianceItem[];
}

export interface QuantityVarianceItem {
  gr_number: string;
  po_number: string;
  supplier: string;
  qty_ordered: number;
  qty_received: number;
  qty_invoiced: number;
  variance_type: "over" | "under" | "match";
}

export interface QuantityVarianceAnalysis {
  total_variances: number;
  over_shipments: number;
  under_shipments: number;
  items: QuantityVarianceItem[];
}

export interface InvoiceMatchDetail {
  invoice: {
    id: number;
    invoice_number: string;
    supplier: string;
    supplier_id: number;
    invoice_amount: number;
    tax_amount: number;
    net_amount: number;
    invoice_date: string;
    due_date: string;
    status: InvoiceStatus;
    match_status: MatchStatus;
    has_exception: boolean;
    exception_type: ExceptionType | null;
    exception_amount: number | null;
    exception_notes: string;
    exception_resolved: boolean;
  };
  purchase_order: {
    id: number;
    po_number: string;
    total_amount: number;
    created_date: string;
    status: POStatus;
  } | null;
  goods_receipt: {
    id: number;
    gr_number: string;
    received_date: string;
    quantity_ordered: number;
    quantity_received: number;
    status: GRStatus;
  } | null;
  variance: {
    price_variance: number | null;
    quantity_variance: number | null;
    total_variance: number | null;
  };
}

export interface ExceptionResolution {
  invoice_id: number;
  invoice_number: string;
  resolved: boolean;
  resolved_at: string;
  resolved_by: string;
}

export interface BulkExceptionResolution {
  resolved_count: number;
  failed_count: number;
  resolved_invoices: number[];
  failed_invoices: { id: number; error: string }[];
}

// Invoice Aging Types
export interface AgingBucket {
  bucket: string;
  count: number;
  amount: number;
  percentage: number;
}

export interface AgingOverview {
  total_ap: number;
  overdue_amount: number;
  current_days_to_pay?: number;
  avg_days_to_pay?: number;
  /** @deprecated use current_days_to_pay */
  current_dpo?: number;
  /** @deprecated use avg_days_to_pay */
  avg_dpo?: number;
  on_time_rate: number;
  buckets: AgingBucket[];
  trend: {
    month: string;
    days_to_pay?: number;
    avg_days_to_pay?: number;
    /** @deprecated use days_to_pay */
    dpo?: number;
    /** @deprecated use avg_days_to_pay */
    avg_dpo?: number;
  }[];
}

export interface AgingBySupplier {
  supplier: string;
  supplier_id: number;
  total_ap: number;
  current: number;
  days_31_60: number;
  days_61_90: number;
  days_90_plus: number;
  avg_days_outstanding: number;
  on_time_rate: number;
}

export interface PaymentTermsCompliance {
  overall_on_time_rate: number;
  early_discount_capture_rate: number;
  discount_amount_captured: number;
  discount_amount_missed: number;
  by_terms: {
    terms: string;
    count: number;
    on_time_rate: number;
  }[];
  by_supplier: {
    supplier: string;
    supplier_id: number;
    on_time_rate: number;
    avg_days_to_pay: number;
  }[];
}

export interface DPOTrend {
  month: string;
  days_to_pay?: number;
  avg_days_to_pay?: number;
  /** @deprecated use days_to_pay / avg_days_to_pay */
  dpo?: number;
  /** @deprecated use avg_days_to_pay */
  avg_dpo?: number;
  invoices_paid?: number;
  invoice_count?: number;
  amount_paid?: number;
  total_amount?: number;
}

export interface CashFlowForecastWeek {
  week: string;
  week_start: string;
  week_end: string;
  amount_due: number;
  invoice_count: number;
  critical_payments: number;
}

export interface CashFlowForecast {
  total_due: number;
  weeks: CashFlowForecastWeek[];
  by_supplier: { supplier: string; amount: number }[];
}

// Purchase Requisition Types
export interface PROverview {
  total_prs: number;
  total_count: number; // Alias for total_prs
  total_value: number;
  conversion_rate: number;
  avg_approval_days: number;
  rejection_rate: number;
  by_status: { status: PRStatus; count: number; value: number }[];
  status_breakdown: Record<string, number>; // Quick lookup by status
}

export interface PRApprovalAnalysis {
  avg_approval_days: number;
  distribution: { range: string; count: number; percentage: number }[];
  approval_time_distribution: {
    range: string;
    count: number;
    percentage: number;
  }[];
  top_approvers: { name: string; count: number; avg_days: number }[];
  bottlenecks: { stage: string; avg_days: number; count: number }[];
}

export interface PRByDepartment {
  department: string;
  pr_count: number;
  count: number; // Alias for pr_count
  total_value: number;
  approval_rate: number;
  avg_processing_days: number;
}

export interface PRPendingItem {
  pr_id: number;
  pr_number: string;
  requestor: string;
  department: string;
  amount: number;
  days_pending: number;
  priority: PRPriority;
  submitted_date: string;
}

export interface PRDetail {
  id: number;
  pr_number: string;
  requested_by: string;
  requestor_name?: string;
  department: string;
  cost_center: string;
  supplier_suggested: string | null;
  suggested_supplier?: string | null;
  category: string | null;
  description: string;
  estimated_amount: number;
  currency: string;
  status: PRStatus;
  priority: PRPriority;
  created_date: string;
  submitted_date: string | null;
  approval_date: string | null;
  approved_by: string | null;
  rejection_reason: string;
  purchase_order: { id: number; po_number: string } | null;
  linked_po_number?: string | null;
}

// Purchase Order Types
export interface POOverview {
  total_pos: number;
  total_count: number;
  total_value: number;
  contract_coverage: number;
  contract_coverage_pct?: number;
  on_contract_value?: number;
  off_contract_value?: number;
  amendment_rate: number;
  avg_po_value: number;
  by_status: { status: POStatus; count: number; value: number }[];
}

export interface POLeakageCategory {
  category: string;
  category_id: number | null;
  maverick_spend: number;
  off_contract_value?: number;
  off_contract_pct?: number;
  total_spend: number;
  total_value?: number;
  maverick_percentage: number;
  supplier_count: number;
}

// POLeakage can be returned as an array of categories OR as object with by_category
export type POLeakage =
  | POLeakageCategory[]
  | {
      total_maverick_spend: number;
      maverick_percentage: number;
      maverick_po_count: number;
      by_category: POLeakageCategory[];
      top_maverick_suppliers: {
        supplier: string;
        supplier_id: number;
        spend: number;
      }[];
      recommendations: string[];
    };

export interface POAmendmentAnalysis {
  amendment_rate: number;
  avg_value_change: number;
  total_amendments: number;
  total_amended?: number;
  total_value_change?: number;
  reasons: { reason: string; count: number; percentage: number }[];
  by_reason?: {
    reason: string;
    count: number;
    avg_change: number;
    total_change: number;
  }[];
  high_amendment_suppliers: {
    supplier: string;
    supplier_id: number;
    amendment_count: number;
    amendment_rate: number;
  }[];
}

export interface POBySupplier {
  supplier: string;
  supplier_id: number;
  po_count: number;
  total_value: number;
  contract_status: "on_contract" | "preferred" | "maverick";
  on_contract_pct?: number;
  on_time_rate: number;
  amendment_rate: number;
}

export interface PODetail {
  id: number;
  po_number: string;
  supplier: string;
  supplier_name?: string;
  supplier_id: number;
  total_amount: number;
  original_amount?: number;
  currency: string;
  tax_amount: number;
  freight_amount: number;
  status: POStatus;
  is_contract_backed: boolean;
  contract: { id: number; contract_number: string } | null;
  contract_number?: string;
  created_date: string;
  approval_date: string | null;
  sent_date: string | null;
  required_date: string | null;
  promised_date: string | null;
  created_by: string;
  approved_by: string | null;
  amendment_count: number;
  requisitions: { id: number; pr_number: string }[];
  linked_prs?: { id: number; pr_number: string }[];
  goods_receipts: { id: number; gr_number: string; status: GRStatus }[];
  invoices: { id: number; invoice_number: string; status: InvoiceStatus }[];
}

// Supplier Payment Performance Types
export interface SupplierPaymentsOverview {
  total_suppliers_with_ap: number;
  total_suppliers?: number;
  overall_on_time_rate: number;
  avg_on_time_rate?: number;
  avg_days_to_pay?: number;
  /** @deprecated use avg_days_to_pay */
  avg_dpo?: number;
  exception_rate: number;
  avg_exception_rate?: number;
  total_ap_balance: number;
}

export interface SupplierPaymentScore {
  supplier: string;
  supplier_id: number;
  ap_balance: number;
  total_ap?: number;
  days_to_pay?: number;
  avg_days_to_pay?: number;
  /** @deprecated use days_to_pay / avg_days_to_pay */
  dpo?: number;
  /** @deprecated use avg_days_to_pay */
  avg_dpo?: number;
  on_time_rate: number;
  exception_rate: number;
  score: number;
  performance_score?: number;
  risk_level: "low" | "medium" | "high";
}

export interface SupplierPaymentDetail {
  supplier: string;
  supplier_id: number;
  total_invoices: number;
  invoice_count?: number;
  total_amount: number;
  ap_balance: number;
  total_ap?: number;
  days_to_pay?: number;
  avg_days_to_pay?: number;
  /** @deprecated use days_to_pay / avg_days_to_pay */
  dpo?: number;
  /** @deprecated use avg_days_to_pay */
  avg_dpo?: number;
  on_time_rate: number;
  exception_count: number;
  exception_rate: number;
  performance_score?: number;
  aging_buckets: AgingBucket[];
  exception_breakdown: { type: ExceptionType; count: number }[];
}

export interface SupplierPaymentHistoryMonth {
  month: string;
  invoices_paid: number;
  amount_paid: number;
  on_time_count: number;
  late_count: number;
}

export interface SupplierPaymentHistoryItem {
  invoice_id: number;
  invoice_number: string;
  invoice_amount?: number;
  amount?: number;
  invoice_date: string;
  due_date: string;
  paid_date: string | null;
  status: InvoiceStatus;
  days_to_pay: number | null;
  on_time?: boolean;
}

// SupplierPaymentHistory can be an object or array
export type SupplierPaymentHistory =
  | {
      supplier: string;
      supplier_id: number;
      monthly_trend: SupplierPaymentHistoryMonth[];
      recent_invoices: SupplierPaymentHistoryItem[];
      exception_history: {
        invoice_id: number;
        invoice_number: string;
        exception_type: ExceptionType;
        amount: number;
        resolved: boolean;
        date: string;
      }[];
    }
  | SupplierPaymentHistoryItem[];

// P2P Analytics API
export const p2pAnalyticsAPI = {
  // P2P Cycle Time Analysis
  getCycleOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PCycleOverview>> =>
    api.get("/analytics/p2p/cycle-overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getCycleByCategory: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PCycleByCategory[]>> =>
    api.get("/analytics/p2p/cycle-by-category/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getCycleBySupplier: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PCycleBySupplier[]>> =>
    api.get("/analytics/p2p/cycle-by-supplier/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getCycleTrends: (
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PCycleTrend[]>> =>
    api.get("/analytics/p2p/cycle-trends/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getBottlenecks: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PBottleneckAnalysis>> =>
    api.get("/analytics/p2p/bottlenecks/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getProcessFunnel: (
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PProcessFunnel>> =>
    api.get("/analytics/p2p/process-funnel/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getStageDrilldown: (
    stage: string,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<P2PStageDrilldown>> =>
    api.get(`/analytics/p2p/stage-drilldown/${stage}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  // 3-Way Matching
  getMatchingOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<MatchingOverview>> =>
    api.get("/analytics/matching/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getMatchingExceptions: (
    params?: {
      status?: "open" | "resolved" | "all";
      exception_type?: ExceptionType;
      limit?: number;
    },
    filters?: AnalyticsFilters,
  ): Promise<
    AxiosResponse<{
      exceptions: InvoiceException[];
      count: number;
      filters: Record<string, string | null>;
    }>
  > =>
    api.get("/analytics/matching/exceptions/", {
      params: {
        ...params,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getExceptionsByType: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ExceptionsByType[]>> =>
    api.get("/analytics/matching/exceptions-by-type/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getExceptionsBySupplier: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<ExceptionsBySupplier[]>> =>
    api.get("/analytics/matching/exceptions-by-supplier/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPriceVarianceAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PriceVarianceAnalysis>> =>
    api.get("/analytics/matching/price-variance/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getQuantityVarianceAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<QuantityVarianceAnalysis>> =>
    api.get("/analytics/matching/quantity-variance/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getInvoiceMatchDetail: (
    invoiceId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<InvoiceMatchDetail>> =>
    api.get(`/analytics/matching/invoice/${invoiceId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  resolveException: (
    invoiceId: number,
    resolutionNotes: string,
  ): Promise<AxiosResponse<ExceptionResolution>> =>
    api.post(
      `/analytics/matching/invoice/${invoiceId}/resolve/`,
      { resolution_notes: resolutionNotes },
      { params: getOrganizationParam() },
    ),

  bulkResolveExceptions: (
    invoiceIds: number[],
    resolutionNotes: string,
  ): Promise<AxiosResponse<BulkExceptionResolution>> =>
    api.post(
      "/analytics/matching/exceptions/bulk-resolve/",
      { invoice_ids: invoiceIds, resolution_notes: resolutionNotes },
      { params: getOrganizationParam() },
    ),

  // Invoice Aging / AP Analysis
  getAgingOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AgingOverview>> =>
    api.get("/analytics/aging/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getAgingBySupplier: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<AgingBySupplier[]>> =>
    api.get("/analytics/aging/by-supplier/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPaymentTermsCompliance: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PaymentTermsCompliance>> =>
    api.get("/analytics/aging/payment-terms-compliance/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getDPOTrends: (
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<DPOTrend[]>> =>
    api.get("/analytics/aging/dpo-trends/", {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getCashFlowForecast: (
    weeks: number = 4,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<CashFlowForecast>> =>
    api.get("/analytics/aging/cash-forecast/", {
      params: {
        weeks,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  // Purchase Requisitions
  getPROverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PROverview>> =>
    api.get("/analytics/requisitions/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPRApprovalAnalysis: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PRApprovalAnalysis>> =>
    api.get("/analytics/requisitions/approval-analysis/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPRByDepartment: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PRByDepartment[]>> =>
    api.get("/analytics/requisitions/by-department/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPRPending: (
    limit: number = 50,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<{ pending_prs: PRPendingItem[]; count: number }>> =>
    api.get("/analytics/requisitions/pending/", {
      params: {
        limit,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getPRDetail: (
    prId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PRDetail>> =>
    api.get(`/analytics/requisitions/${prId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  // Purchase Orders
  getPOOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<POOverview>> =>
    api.get("/analytics/purchase-orders/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPOLeakage: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<POLeakage>> =>
    api.get("/analytics/purchase-orders/leakage/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPOAmendments: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<POAmendmentAnalysis>> =>
    api.get("/analytics/purchase-orders/amendments/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPOBySupplier: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<POBySupplier[]>> =>
    api.get("/analytics/purchase-orders/by-supplier/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getPODetail: (
    poId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<PODetail>> =>
    api.get(`/analytics/purchase-orders/${poId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  // Supplier Payment Performance
  getSupplierPaymentsOverview: (
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierPaymentsOverview>> =>
    api.get("/analytics/supplier-payments/overview/", {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSupplierPaymentsScorecard: (
    limit: number = 50,
    filters?: AnalyticsFilters,
  ): Promise<
    AxiosResponse<{ suppliers: SupplierPaymentScore[]; count: number }>
  > =>
    api.get("/analytics/supplier-payments/scorecard/", {
      params: {
        limit,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),

  getSupplierPaymentDetail: (
    supplierId: number,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierPaymentDetail>> =>
    api.get(`/analytics/supplier-payments/${supplierId}/`, {
      params: { ...getOrganizationParam(), ...buildFilterParams(filters) },
    }),

  getSupplierPaymentHistory: (
    supplierId: number,
    months: number = 12,
    filters?: AnalyticsFilters,
  ): Promise<AxiosResponse<SupplierPaymentHistory>> =>
    api.get(`/analytics/supplier-payments/${supplierId}/history/`, {
      params: {
        months,
        ...getOrganizationParam(),
        ...buildFilterParams(filters),
      },
    }),
};

export default api;
