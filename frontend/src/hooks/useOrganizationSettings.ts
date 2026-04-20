/**
 * Hooks for organization-level settings (admin only)
 *
 * Provides React Query hooks for managing organization savings configuration.
 * These settings control the industry-benchmark rates used by AI Insights.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  authAPI,
  type SavingsConfig,
  type SavingsConfigResponse,
  type BenchmarkProfile,
} from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useOrganization } from "@/contexts/OrganizationContext";

/**
 * Get the savings configuration for the current organization.
 *
 * Returns:
 * - savings_config: Raw config stored on organization
 * - effective_config: Merged config with profile defaults applied
 * - available_profiles: The three preset profiles (conservative/moderate/aggressive)
 */
export function useOrganizationSavingsConfig() {
  const { activeOrganization } = useOrganization();
  const orgId = activeOrganization?.id;

  return useQuery({
    queryKey: queryKeys.orgSettings.savingsConfig(orgId ?? 0),
    queryFn: async (): Promise<SavingsConfigResponse> => {
      if (!orgId) {
        throw new Error("No organization selected");
      }
      const response = await authAPI.getSavingsConfig(orgId);
      return response.data;
    },
    enabled: !!orgId,
    staleTime: 5 * 60 * 1000, // 5 minutes - config changes infrequently
  });
}

/**
 * Update the savings configuration for the current organization.
 *
 * On success:
 * - Invalidates the savings config query
 * - Invalidates AI insights queries (they use the config)
 */
export function useUpdateOrganizationSavingsConfig() {
  const queryClient = useQueryClient();
  const { activeOrganization } = useOrganization();
  const orgId = activeOrganization?.id;

  return useMutation({
    mutationFn: async (config: Partial<SavingsConfig>) => {
      if (!orgId) {
        throw new Error("No organization selected");
      }
      const response = await authAPI.updateSavingsConfig(orgId, config);
      return response.data;
    },
    onSuccess: () => {
      if (orgId) {
        // Invalidate savings config
        queryClient.invalidateQueries({
          queryKey: queryKeys.orgSettings.savingsConfig(orgId),
        });
        // Invalidate AI insights (they use these rates)
        queryClient.invalidateQueries({
          queryKey: queryKeys.ai.all,
        });
      }
    },
  });
}

/**
 * Helper: Get display label for benchmark profile
 */
export function getBenchmarkProfileLabel(profile: BenchmarkProfile): string {
  const labels: Record<BenchmarkProfile, string> = {
    conservative: "Conservative (Risk-averse, 85-95% realization)",
    moderate: "Moderate (Balanced approach, 70-85% realization)",
    aggressive: "Aggressive (Mature procurement, 50-70% realization)",
    custom: "Custom (Set your own rates)",
  };
  return labels[profile];
}

/**
 * Helper: Get description for benchmark profile
 */
export function getBenchmarkProfileDescription(
  profile: BenchmarkProfile,
): string {
  const descriptions: Record<BenchmarkProfile, string> = {
    conservative:
      "Uses lower end of industry benchmark ranges. Best for organizations new to procurement optimization or with limited negotiation leverage.",
    moderate:
      "Uses mid-range industry benchmarks. Suitable for most organizations with established procurement processes.",
    aggressive:
      "Uses higher end of industry benchmarks. Best for mature procurement teams with strong supplier relationships and proven track records.",
    custom:
      "Configure individual rates based on your organization's specific circumstances and historical performance.",
  };
  return descriptions[profile];
}

/**
 * Benchmark ranges for industry comparison
 * These represent the min/max of industry benchmarks from research sources
 */
export const BENCHMARK_RANGES: Record<
  string,
  { min: number; max: number; unit: "percent" | "currency" }
> = {
  consolidation_rate: { min: 0.01, max: 0.08, unit: "percent" },
  anomaly_recovery_rate: { min: 0.005, max: 0.015, unit: "percent" },
  price_variance_capture: { min: 0.2, max: 0.8, unit: "percent" },
  specification_rate: { min: 0.02, max: 0.04, unit: "percent" },
  payment_terms_rate: { min: 0.005, max: 0.012, unit: "percent" },
  process_savings_per_txn: { min: 25, max: 50, unit: "currency" },
};

/**
 * Realization probability for each benchmark profile
 * Based on historical procurement success rates
 */
export const PROFILE_REALIZATION: Record<
  Exclude<BenchmarkProfile, "custom">,
  { probability: number; range: string; variant: "default" | "secondary" | "destructive" }
> = {
  conservative: { probability: 0.9, range: "85-95%", variant: "default" },
  moderate: { probability: 0.75, range: "70-85%", variant: "secondary" },
  aggressive: { probability: 0.55, range: "50-70%", variant: "destructive" },
};

/**
 * Helper: Format rate as percentage string
 */
export function formatRateAsPercentage(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

/**
 * Helper: Format rate as currency per transaction
 */
export function formatRateAsCurrency(rate: number): string {
  return `$${rate.toFixed(0)}/txn`;
}

/**
 * Helper: Get the benchmark range string for a rate key
 */
export function getBenchmarkRangeString(key: string): string | null {
  const range = BENCHMARK_RANGES[key];
  if (!range) return null;

  if (range.unit === "percent") {
    return `${(range.min * 100).toFixed(1)}% - ${(range.max * 100).toFixed(1)}%`;
  }
  return `$${range.min} - $${range.max}`;
}

/**
 * Export savings configuration as PDF for stakeholder presentations.
 *
 * Downloads a PDF containing:
 * - Organization name and benchmark profile
 * - Current effective rates with industry ranges
 * - Source citations
 */
export function useExportSavingsConfigPdf() {
  const { activeOrganization } = useOrganization();

  return useMutation({
    mutationFn: async () => {
      if (!activeOrganization?.id) {
        throw new Error("No organization selected");
      }
      const response = await authAPI.exportSavingsConfigPdf(activeOrganization.id);
      const blob = response.data;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeOrganization.slug || "organization"}-benchmark-summary.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}
