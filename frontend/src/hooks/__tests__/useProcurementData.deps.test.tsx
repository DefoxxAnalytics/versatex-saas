/**
 * Finding E2: useProcurementData listener must rebind when orgId changes.
 *
 * Bug: useFilteredProcurementData's useEffect closes over orgId but omits it
 * from the dep array. After a superuser org-switch, getOrgKeyPart() returns a
 * new value, but the listener still holds the prior orgId in its closure.
 * The next "filtersUpdated" event therefore invalidates the OLD org's
 * queryKey; the new org's filtered view stays stale until remount.
 *
 * Regression test: rerender the hook with a different orgId, dispatch the
 * event, and assert that invalidateQueries was called with the NEW org's key.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useFilteredProcurementData } from "../useProcurementData";
import * as api from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

vi.mock("@/lib/api", () => ({
  procurementAPI: {
    getTransactions: vi.fn(),
  },
  getOrganizationParam: vi.fn(),
}));

vi.mock("@/lib/analytics", () => ({
  applyFilters: vi.fn((data) => data),
}));

describe("useFilteredProcurementData - Finding E2 useEffect deps", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
      data: { results: [] },
    } as never);
  });

  it("rebinds the filtersUpdated listener after orgId changes", async () => {
    // #given a hook initially rendered for org 1
    vi.mocked(api.getOrganizationParam).mockReturnValue({ organization_id: 1 });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { rerender } = renderHook(() => useFilteredProcurementData(), {
      wrapper,
    });

    // Wait for initial mount to register the listener.
    await waitFor(() => {
      expect(api.procurementAPI.getTransactions).toHaveBeenCalled();
    });

    // #when org switches to org 2 and the hook re-renders
    vi.mocked(api.getOrganizationParam).mockReturnValue({ organization_id: 2 });
    invalidateSpy.mockClear();
    rerender();

    // #and a filtersUpdated event fires after the org switch
    await act(async () => {
      window.dispatchEvent(new CustomEvent("filtersUpdated"));
    });

    // #then the listener must invalidate the NEW org's filtered key, not org 1's
    const expectedNewKey = queryKeys.procurement.filtered(2);
    const expectedOldKey = queryKeys.procurement.filtered(1);

    const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);

    const calledWithNew = calls.some(
      (k) => JSON.stringify(k) === JSON.stringify(expectedNewKey),
    );
    const calledWithOld = calls.some(
      (k) => JSON.stringify(k) === JSON.stringify(expectedOldKey),
    );

    expect(calledWithNew).toBe(true);
    expect(calledWithOld).toBe(false);
  });
});
