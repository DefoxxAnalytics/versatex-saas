/**
 * Finding E1: useResolveViolation must invalidate the correct query keys.
 *
 * Bug: invalidates ["policy-violations"], ["compliance-overview"],
 * ["supplier-compliance-scores"] - but factory keys are nested under
 * ["compliance", ...]. Prefix-match matches nothing. UI stays stale.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useResolveViolation } from "../useCompliance";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  analyticsAPI: {
    resolveViolation: vi.fn(),
  },
  getOrganizationParam: vi.fn(() => ({})),
}));

describe("useResolveViolation - Finding E1 invalidation keys", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("invalidates the correct compliance query keys after a successful resolve", async () => {
    // #given
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    vi.mocked(api.analyticsAPI.resolveViolation).mockResolvedValue({
      data: {
        id: 1,
        is_resolved: true,
        resolved_at: "2026-05-06T00:00:00Z",
        resolution_notes: "Fixed",
      },
    } as never);

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useResolveViolation(), { wrapper });

    // #when
    await act(async () => {
      await result.current.mutateAsync({
        violationId: 1,
        resolutionNotes: "Fixed",
      });
    });

    // #then
    const invalidatedKeys = invalidateSpy.mock.calls
      .map(([opts]) => opts?.queryKey)
      .filter((key): key is readonly unknown[] => Array.isArray(key));

    // Each invalidation must start with "compliance" (the factory prefix).
    expect(invalidatedKeys.length).toBeGreaterThan(0);
    expect(invalidatedKeys.every((key) => key[0] === "compliance")).toBe(true);

    // Either the umbrella ["compliance"] key OR all three specific prefixes
    // must be invalidated (both satisfy prefix-match for the buggy queries).
    const hasUmbrella = invalidatedKeys.some(
      (key) => key.length === 1 && key[0] === "compliance",
    );
    const hasViolations =
      hasUmbrella ||
      invalidatedKeys.some(
        (key) => key[0] === "compliance" && key[1] === "violations",
      );
    const hasOverview =
      hasUmbrella ||
      invalidatedKeys.some(
        (key) => key[0] === "compliance" && key[1] === "overview",
      );
    const hasSupplierScores =
      hasUmbrella ||
      invalidatedKeys.some(
        (key) => key[0] === "compliance" && key[1] === "supplier-scores",
      );

    expect(hasViolations).toBe(true);
    expect(hasOverview).toBe(true);
    expect(hasSupplierScores).toBe(true);

    // The buggy literals must NOT be invalidated.
    const containsBuggyLiteral = invalidatedKeys.some(
      (key) =>
        key[0] === "policy-violations" ||
        key[0] === "compliance-overview" ||
        key[0] === "supplier-compliance-scores",
    );
    expect(containsBuggyLiteral).toBe(false);
  });
});
