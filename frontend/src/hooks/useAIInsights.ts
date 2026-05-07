/**
 * Custom hooks for AI Insights data from Django API
 *
 * All hooks include organization_id in query keys to properly
 * invalidate cache when switching organizations (superuser feature).
 *
 * Filter support: AI Insights hooks now accept filters from the FilterPane
 * via the useAnalyticsFilters() hook. Filters are passed to backend APIs
 * and included in query keys for proper cache invalidation.
 *
 * Features:
 * - Structured AI enhancement from tool calling
 * - Redis caching with cache_hit indicator
 * - Manual refresh support to bypass cache
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analyticsAPI, authAPI, getOrganizationParam } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { useAnalyticsFilters } from "./useAnalytics";
import type {
  AIInsight,
  AIInsightType,
  AIEnhancement,
  AIRecommendation,
  AIImpactLevel,
  AIEffortLevel,
  InsightFeedbackRequest,
  InsightOutcomeUpdateRequest,
  InsightActionTaken,
  InsightOutcome,
  InsightFeedbackItem,
  InsightEffectivenessMetrics,
} from "@/lib/api";

/**
 * Get the current organization ID for query key inclusion.
 * Returns undefined if viewing own org (default behavior).
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

/**
 * Get all AI insights combined with optional AI enhancement
 */
export function useAIInsights() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.ai.insights(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getAIInsights(false, filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes (expensive computation)
    retry: 2,
  });
}

/**
 * Mutation to force refresh AI insights (bypasses backend cache)
 */
export function useRefreshAIInsights() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();

  return useMutation({
    mutationFn: async () => {
      const response = await analyticsAPI.getAIInsights(true, filters);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.ai.insights(orgId, filters), data);
    },
  });
}

/**
 * Get cost optimization insights only
 */
export function useAIInsightsCost() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.ai.insightsCost(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getAIInsightsCost(filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get supplier risk insights only
 */
export function useAIInsightsRisk() {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.ai.insightsRisk(orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getAIInsightsRisk(filters);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get anomaly detection insights
 */
export function useAIInsightsAnomalies(sensitivity: number = 2.0) {
  const orgId = getOrgKeyPart();
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: queryKeys.ai.insightsAnomalies(sensitivity, orgId, filters),
    queryFn: async () => {
      const response = await analyticsAPI.getAIInsightsAnomalies(
        sensitivity,
        filters,
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Filter insights by type
 */
export function filterInsightsByType(
  insights: AIInsight[],
  type: AIInsightType | "all",
): AIInsight[] {
  if (type === "all") return insights;
  return insights.filter((insight) => insight.type === type);
}

/**
 * Sort insights by severity and potential savings
 */
export function sortInsights(insights: AIInsight[]): AIInsight[] {
  const severityOrder = { high: 0, medium: 1, low: 2 };
  return [...insights].sort((a, b) => {
    // First sort by severity
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
    if (severityDiff !== 0) return severityDiff;
    // Then by potential savings (descending)
    return b.potential_savings - a.potential_savings;
  });
}

/**
 * Get insight type display label
 */
export function getInsightTypeLabel(type: AIInsightType): string {
  const labels: Record<AIInsightType, string> = {
    cost_optimization: "Cost Optimization",
    risk: "Supplier Risk",
    anomaly: "Anomaly",
    consolidation: "Consolidation",
  };
  return labels[type] || type;
}

/**
 * Get insight type icon color
 */
export function getInsightTypeColor(type: AIInsightType): string {
  const colors: Record<AIInsightType, string> = {
    cost_optimization: "text-green-600 bg-green-100",
    risk: "text-red-600 bg-red-100",
    anomaly: "text-yellow-600 bg-yellow-100",
    consolidation: "text-blue-600 bg-blue-100",
  };
  return colors[type] || "text-gray-600 bg-gray-100";
}

/**
 * Get severity badge color
 */
export function getSeverityColor(severity: "high" | "medium" | "low"): string {
  const colors = {
    high: "bg-red-100 text-red-800 border-red-200",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
    low: "bg-green-100 text-green-800 border-green-200",
  };
  return colors[severity];
}

/**
 * Get impact level badge color for AI recommendations
 */
export function getImpactColor(impact: AIImpactLevel): string {
  const colors: Record<AIImpactLevel, string> = {
    high: "bg-green-100 text-green-800 border-green-200",
    medium: "bg-blue-100 text-blue-800 border-blue-200",
    low: "bg-gray-100 text-gray-800 border-gray-200",
  };
  return colors[impact];
}

/**
 * Get effort level badge color for AI recommendations
 */
export function getEffortColor(effort: AIEffortLevel): string {
  const colors: Record<AIEffortLevel, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
  };
  return colors[effort];
}

/**
 * Get risk level color for AI risk assessment
 */
export function getRiskLevelColor(
  level: "critical" | "high" | "moderate" | "low",
): string {
  const colors = {
    critical: "bg-red-600 text-white",
    high: "bg-red-100 text-red-800",
    moderate: "bg-yellow-100 text-yellow-800",
    low: "bg-green-100 text-green-800",
  };
  return colors[level];
}

/**
 * Sort recommendations by impact/effort ratio (high impact, low effort first)
 */
export function sortRecommendationsByValue(
  recommendations: AIRecommendation[],
): AIRecommendation[] {
  const impactScore: Record<AIImpactLevel, number> = {
    high: 3,
    medium: 2,
    low: 1,
  };
  const effortScore: Record<AIEffortLevel, number> = {
    low: 3,
    medium: 2,
    high: 1,
  };

  return [...recommendations].sort((a, b) => {
    const aValue = impactScore[a.impact] * effortScore[a.effort];
    const bValue = impactScore[b.impact] * effortScore[b.effort];
    return bValue - aValue;
  });
}

// ============================================================================
// AI Insight Feedback Hooks (ROI Tracking)
// ============================================================================

/**
 * Record user action on an AI insight
 */
export function useRecordInsightFeedback() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async (data: InsightFeedbackRequest) => {
      const response = await analyticsAPI.recordInsightFeedback(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightFeedback(undefined, orgId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightEffectiveness(orgId),
      });
    },
  });
}

/**
 * Update the outcome of a previously recorded insight action
 */
export function useUpdateInsightOutcome() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async ({
      feedbackId,
      data,
    }: {
      feedbackId: string;
      data: InsightOutcomeUpdateRequest;
    }) => {
      const response = await analyticsAPI.updateInsightOutcome(
        feedbackId,
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightFeedback(undefined, orgId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightEffectiveness(orgId),
      });
    },
  });
}

/**
 * Delete an insight feedback entry.
 * Only the creator or an admin can delete feedback.
 */
export function useDeleteInsightFeedback() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async (feedbackId: string) => {
      const response = await analyticsAPI.deleteInsightFeedback(feedbackId);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightFeedback(undefined, orgId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.insightEffectiveness(orgId),
      });
    },
  });
}

/**
 * Get effectiveness metrics for AI insights
 */
export function useInsightEffectiveness() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.ai.insightEffectiveness(orgId),
    queryFn: async () => {
      const response = await analyticsAPI.getInsightEffectiveness();
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  });
}

/**
 * List insight feedback with optional filters
 */
export function useInsightFeedbackList(params?: {
  insight_type?: AIInsightType;
  action_taken?: InsightActionTaken;
  outcome?: InsightOutcome;
  limit?: number;
  offset?: number;
}) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.ai.insightFeedback(params, orgId),
    queryFn: async () => {
      const response = await analyticsAPI.listInsightFeedback(params);
      return response.data;
    },
    staleTime: 60 * 1000, // Cache for 1 minute
  });
}

/**
 * Get action taken display label
 */
export function getActionLabel(action: InsightActionTaken): string {
  const labels: Record<InsightActionTaken, string> = {
    implemented: "Implemented",
    dismissed: "Dismissed",
    deferred: "Deferred",
    investigating: "Investigating",
    partial: "Partially Implemented",
  };
  return labels[action] || action;
}

/**
 * Get action taken badge color
 */
export function getActionColor(action: InsightActionTaken): string {
  const colors: Record<InsightActionTaken, string> = {
    implemented: "bg-green-100 text-green-800 border-green-200",
    dismissed: "bg-gray-100 text-gray-800 border-gray-200",
    deferred: "bg-yellow-100 text-yellow-800 border-yellow-200",
    investigating: "bg-blue-100 text-blue-800 border-blue-200",
    partial: "bg-purple-100 text-purple-800 border-purple-200",
  };
  return colors[action] || "bg-gray-100 text-gray-800 border-gray-200";
}

/**
 * Get outcome display label
 */
export function getOutcomeLabel(outcome: InsightOutcome): string {
  const labels: Record<InsightOutcome, string> = {
    pending: "Pending",
    success: "Success",
    partial_success: "Partial Success",
    no_change: "No Change",
    failed: "Failed",
  };
  return labels[outcome] || outcome;
}

/**
 * Get outcome badge color
 */
export function getOutcomeColor(outcome: InsightOutcome): string {
  const colors: Record<InsightOutcome, string> = {
    pending: "bg-gray-100 text-gray-600",
    success: "bg-green-100 text-green-800",
    partial_success: "bg-yellow-100 text-yellow-800",
    no_change: "bg-orange-100 text-orange-800",
    failed: "bg-red-100 text-red-800",
  };
  return colors[outcome] || "bg-gray-100 text-gray-600";
}

// ============================================================================
// Async AI Enhancement Hooks
// ============================================================================

/**
 * Request async AI enhancement for insights
 */
export function useRequestAsyncEnhancement() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async (insights: AIInsight[]) => {
      const response = await analyticsAPI.requestAsyncEnhancement({ insights });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.asyncEnhancementStatus(orgId),
      });
    },
  });
}

/**
 * Poll for async AI enhancement status
 *
 * @param enabled - Whether to enable polling
 * @param pollInterval - Polling interval in ms (default: 2000)
 */
export function useAsyncEnhancementStatus(
  enabled: boolean = true,
  pollInterval: number = 2000,
) {
  const orgId = getOrgKeyPart();

  return useQuery({
    queryKey: queryKeys.ai.asyncEnhancementStatus(orgId),
    queryFn: async () => {
      const response = await analyticsAPI.getAsyncEnhancementStatus();
      return response.data;
    },
    enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "processing" || data?.status === "queued") {
        return pollInterval;
      }
      return false;
    },
    staleTime: 0,
    retry: false,
  });
}

// ============================================================================
// Deep Analysis Hooks
// ============================================================================

/**
 * Request deep analysis for a specific insight
 */
export function useRequestDeepAnalysis() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async (insight: AIInsight) => {
      const response = await analyticsAPI.requestDeepAnalysis({ insight });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.deepAnalysisStatus(data.insight_id, orgId),
      });
    },
  });
}

/**
 * Poll for deep analysis status for a specific insight
 *
 * @param insightId - The insight ID to check status for
 * @param enabled - Whether to enable polling
 * @param pollInterval - Polling interval in ms (default: 2000)
 */
export function useDeepAnalysisStatus(
  insightId: string | null,
  enabled: boolean = true,
  pollInterval: number = 2000,
) {
  const orgId = getOrgKeyPart();

  return useQuery({
    queryKey: queryKeys.ai.deepAnalysisStatus(insightId, orgId),
    queryFn: async () => {
      if (!insightId) throw new Error("Insight ID required");
      const response = await analyticsAPI.getDeepAnalysisStatus(insightId);
      return response.data;
    },
    enabled: enabled && !!insightId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "processing") {
        return pollInterval;
      }
      return false;
    },
    staleTime: 0,
    retry: false,
  });
}

/**
 * Get risk level color for deep analysis risk factors
 */
export function getDeepAnalysisRiskColor(
  likelihood: "high" | "medium" | "low",
  impact: "high" | "medium" | "low",
): string {
  const score =
    (likelihood === "high" ? 3 : likelihood === "medium" ? 2 : 1) *
    (impact === "high" ? 3 : impact === "medium" ? 2 : 1);

  if (score >= 6) return "bg-red-100 text-red-800 border-red-200";
  if (score >= 4) return "bg-yellow-100 text-yellow-800 border-yellow-200";
  return "bg-green-100 text-green-800 border-green-200";
}

/**
 * Get phase status color for implementation roadmap
 */
export function getPhaseColor(phaseIndex: number, totalPhases: number): string {
  const colors = [
    "bg-blue-100 text-blue-800 border-blue-200",
    "bg-indigo-100 text-indigo-800 border-indigo-200",
    "bg-purple-100 text-purple-800 border-purple-200",
    "bg-violet-100 text-violet-800 border-violet-200",
  ];
  return colors[phaseIndex % colors.length];
}

// =============================================================================
// AI Chat Streaming Hooks
// =============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatStreamState {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  usage: { input_tokens?: number; output_tokens?: number } | null;
}

/**
 * Typed SSE error codes emitted by the backend's streaming endpoints.
 *
 * Mirrors `apps/analytics/llm_error_codes.AIErrorCode`. When the backend
 * cannot produce tokens, it emits a frame `{error_code, error}` so the UI
 * can branch on the code (and not parse free-text).
 */
export const SSE_ERROR_CODE_MESSAGES: Record<string, string> = {
  auth_error: "AI authentication failed. Update the API key in Settings.",
  rate_limited: "AI service is rate limited. Try again shortly.",
  service_unavailable: "AI service is temporarily unavailable.",
  bad_request: "AI request was rejected.",
  unknown: "AI service error. See server logs.",
};

interface StreamEvent {
  token?: string;
  done?: boolean;
  error?: string;
  error_code?: string;
  usage?: { input_tokens: number; output_tokens: number };
}

/**
 * Pick the user-facing message for a streaming error frame.
 *
 * Prefers the typed `error_code` mapping (frontend owns the copy) and falls
 * back to the server-provided `error` string, then a generic default.
 */
function resolveStreamErrorMessage(data: StreamEvent): string {
  if (data.error_code && SSE_ERROR_CODE_MESSAGES[data.error_code]) {
    return SSE_ERROR_CODE_MESSAGES[data.error_code];
  }
  return data.error || "Unknown error";
}

/**
 * Hook for streaming AI chat responses.
 *
 * Provides real-time streaming from the SSE endpoint with message history management.
 */
export function useAIChatStream() {
  const [state, setState] = useState<ChatStreamState>({
    messages: [],
    isStreaming: false,
    error: null,
    usage: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  // v3.1 Phase 1 (F-C1): ref tracks the latest messages alongside React
  // state so the sendMessage callback can read fresh history without
  // re-creating the callback (and remounting consumers) on every message.
  // Previously `useCallback(..., [state.messages])` captured a snapshot;
  // a fast follow-up sent before React flushed the setState would land
  // with stale history, breaking LLM context for the second turn.
  const messagesRef = useRef<ChatMessage[]>([]);

  const sendMessage = useCallback(
    async (content: string, context?: Record<string, unknown>) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      // Snapshot history BEFORE the optimistic append so we send only
      // {prior history + the new user turn} — not the placeholder
      // assistant message we're about to render.
      const messagesToSend = [...messagesRef.current, userMessage].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      setState((prev) => {
        const next = [...prev.messages, userMessage, assistantMessage];
        messagesRef.current = next;
        return {
          ...prev,
          messages: next,
          isStreaming: true,
          error: null,
        };
      });

      abortControllerRef.current = new AbortController();

      // Helper kept inline so the closure over assistantMessage.id is
      // colocated. Updates messagesRef in lockstep with setState so the
      // ref never lags the rendered UI.
      const applyMessages = (
        updater: (msgs: ChatMessage[]) => ChatMessage[],
        patch: Partial<Omit<ChatStreamState, "messages">> = {},
      ) => {
        setState((prev) => {
          const messages = updater(prev.messages);
          messagesRef.current = messages;
          return { ...prev, ...patch, messages };
        });
      };

      try {
        const apiUrl =
          import.meta.env.VITE_API_URL || "http://127.0.0.1:8001/api";

        // v3.1 Phase 1 (F-H1): if the access cookie expires mid-session, the
        // SSE fetch returns 401 — but unlike the axios interceptor it has no
        // retry. Refresh once, retry once, then surface the failure. Retry
        // is bounded so a genuinely-broken auth state doesn't loop.
        const openStream = async (): Promise<Response> =>
          fetch(`${apiUrl}/v1/analytics/ai-insights/chat/stream/`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              messages: messagesToSend,
              context: context || {},
            }),
            signal: abortControllerRef.current!.signal,
          });

        let response = await openStream();
        if (response.status === 401) {
          try {
            await authAPI.refreshToken();
            response = await openStream();
          } catch {
            // refreshToken failure: fall through, surface 401 below.
          }
        }

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let fullContent = "";
        // v3.1 Phase 1 (F-H2): reader buffer for SSE events split across
        // TCP boundaries. Without this, a `data: {...}` line that arrives
        // in two chunks gets JSON.parse-rejected and silently dropped via
        // the catch — visible to users as missing tokens / empty replies.
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            // Flush the trailing buffer in case the stream ended without a
            // final newline.
            buffer += decoder.decode();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last (possibly incomplete) line for the next iteration.
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const data: StreamEvent = JSON.parse(line.slice(6));

              if (data.error || data.error_code) {
                applyMessages((m) => m, {
                  isStreaming: false,
                  error: resolveStreamErrorMessage(data),
                });
                return;
              }

              if (data.token) {
                fullContent += data.token;
                applyMessages((msgs) =>
                  msgs.map((m) =>
                    m.id === assistantMessage.id
                      ? { ...m, content: fullContent }
                      : m,
                  ),
                );
              }

              if (data.done) {
                applyMessages(
                  (msgs) =>
                    msgs.map((m) =>
                      m.id === assistantMessage.id
                        ? { ...m, isStreaming: false }
                        : m,
                    ),
                  { isStreaming: false, usage: data.usage || null },
                );
              }
            } catch {
              // Truly malformed SSE frame — log via dev tools, skip.
            }
          }
        }
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          applyMessages((m) => m, {
            isStreaming: false,
            error: (error as Error).message,
          });
        }
      }
    },
    [],
  );

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
    setState((prev) => ({
      ...prev,
      isStreaming: false,
      messages: prev.messages.map((m) =>
        m.isStreaming ? { ...m, isStreaming: false } : m,
      ),
    }));
  }, []);

  // v3.1 Phase 2 (F-M3): abort any in-flight stream on unmount. Without
  // this, navigating away mid-stream leaves the fetch + reader running:
  // the assistant message keeps consuming LLM credits and the eventual
  // setState fires on an unmounted component (React 18 warning, prod
  // memory leak). cancelStream is consumer-driven and didn't fire here.
  useEffect(() => {
    const controller = abortControllerRef;
    return () => {
      controller.current?.abort();
    };
  }, []);

  const clearMessages = useCallback(() => {
    setState({
      messages: [],
      isStreaming: false,
      error: null,
      usage: null,
    });
  }, []);

  return {
    ...state,
    sendMessage,
    cancelStream,
    clearMessages,
  };
}

/**
 * Hook for quick single-turn queries.
 *
 * Simpler than full chat for one-off questions about procurement data.
 */
export function useAIQuickQuery() {
  const [state, setState] = useState<{
    response: string;
    isStreaming: boolean;
    error: string | null;
  }>({
    response: "",
    isStreaming: false,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const query = useCallback(
    async (queryText: string, includeContext = true) => {
      setState({ response: "", isStreaming: true, error: null });

      abortControllerRef.current = new AbortController();

      try {
        const apiUrl =
          import.meta.env.VITE_API_URL || "http://127.0.0.1:8001/api";

        const response = await fetch(
          `${apiUrl}/v1/analytics/ai-insights/chat/quick/`,
          {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              query: queryText,
              include_context: includeContext,
            }),
            signal: abortControllerRef.current.signal,
          },
        );

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let fullContent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data: StreamEvent = JSON.parse(line.slice(6));

                if (data.error || data.error_code) {
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    error: resolveStreamErrorMessage(data),
                  }));
                  return;
                }

                if (data.token) {
                  fullContent += data.token;
                  setState((prev) => ({ ...prev, response: fullContent }));
                }

                if (data.done) {
                  setState((prev) => ({ ...prev, isStreaming: false }));
                }
              } catch {
                // Ignore parse errors
              }
            }
          }
        }
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setState((prev) => ({
            ...prev,
            isStreaming: false,
            error: (error as Error).message,
          }));
        }
      }
    },
    [],
  );

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  return {
    ...state,
    query,
    cancel,
  };
}

// =============================================================================
// LLM Usage & Cost Tracking Hooks
// =============================================================================

/**
 * Get LLM usage summary for cost monitoring
 */
export function useLLMUsageSummary(days: number = 30) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.ai.usageSummary(days, orgId),
    queryFn: async () => {
      const response = await analyticsAPI.getLLMUsageSummary(days);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get daily LLM usage data for trend charts
 */
export function useLLMUsageDaily(days: number = 30) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: queryKeys.ai.usageDaily(days, orgId),
    queryFn: async () => {
      const response = await analyticsAPI.getLLMUsageDaily(days);
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Format cost for display
 */
export function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  if (cost < 1) return `$${cost.toFixed(3)}`;
  return `$${cost.toFixed(2)}`;
}

/**
 * Format large numbers with K/M suffix
 */
export function formatTokenCount(count: number): string {
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return count.toString();
}

/**
 * Get request type display label
 */
export function getRequestTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    enhance: "Enhancement",
    single_insight: "Single Analysis",
    deep_analysis: "Deep Analysis",
    classify: "Classification",
    chat: "Chat",
    health_check: "Health Check",
  };
  return labels[type] || type;
}

/**
 * Get request type color
 */
export function getRequestTypeColor(type: string): string {
  const colors: Record<string, string> = {
    enhance: "bg-blue-100 text-blue-800",
    single_insight: "bg-purple-100 text-purple-800",
    deep_analysis: "bg-indigo-100 text-indigo-800",
    classify: "bg-gray-100 text-gray-800",
    chat: "bg-green-100 text-green-800",
    health_check: "bg-yellow-100 text-yellow-800",
  };
  return colors[type] || "bg-gray-100 text-gray-800";
}

/**
 * Get provider display label
 */
export function getProviderLabel(provider: string): string {
  const labels: Record<string, string> = {
    anthropic: "Anthropic Claude",
    openai: "OpenAI GPT",
  };
  return labels[provider] || provider;
}

// Re-export types for convenience
export type {
  AIEnhancement,
  AIRecommendation,
  AIImpactLevel,
  AIEffortLevel,
  InsightActionTaken,
  InsightOutcome,
  InsightFeedbackItem,
  InsightEffectivenessMetrics,
  // Async Enhancement types
  AsyncEnhancementStatus,
  AsyncEnhancementStatusResponse,
  // Deep Analysis types
  DeepAnalysis,
  DeepAnalysisStatus,
  DeepAnalysisStatusResponse,
  DeepAnalysisRootCause,
  DeepAnalysisPhase,
  DeepAnalysisFinancialImpact,
  DeepAnalysisRiskFactor,
  DeepAnalysisSuccessMetric,
  // LLM Usage types
  LLMUsageSummary,
  LLMUsageDailyResponse,
  LLMUsageDailyEntry,
  LLMUsageByType,
  LLMUsageByProvider,
} from "@/lib/api";
