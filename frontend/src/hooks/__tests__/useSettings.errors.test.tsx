/**
 * Finding E6: useSettings save / reset must surface backend failures.
 *
 * Bug: catch handlers used console.debug — invisible in default devtools.
 * Optimistic localStorage save makes the UI claim success even when
 * the backend 500s. After the fix:
 *   - The save mutation rejects so consumers see mutation.error.
 *   - The reset mutation rejects similarly.
 *   - Both surface a toast.error so the user knows the sync failed.
 *   - localStorage is still updated (intentional optimistic design).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "sonner";
import * as api from "@/lib/api";
import { useUpdateSettings, useResetSettings } from "../useSettings";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("@/lib/api", () => ({
  authAPI: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    replacePreferences: vi.fn(),
  },
}));

const SETTINGS_STORAGE_KEY = "user-settings";
const USER_KEY = "user";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useSettings — Finding E6 error surfacing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("useUpdateSettings save failure", () => {
    it("calls toast.error and exposes mutation.error when backend save rejects", async () => {
      // #given a logged-in user and a backend that 500s
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      vi.mocked(api.authAPI.updatePreferences).mockRejectedValueOnce(
        new Error("HTTP 500: Internal Server Error"),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      // #when the user updates a setting
      await act(async () => {
        try {
          await result.current.mutateAsync({ theme: "dark" });
        } catch {
          // mutation should reject so consumers can chain onError
        }
      });

      // #then a toast.error is shown and mutation.error is non-null
      await waitFor(() => {
        expect(vi.mocked(toast.error)).toHaveBeenCalled();
      });
      expect(result.current.error).toBeTruthy();
      expect(result.current.error?.message).toContain("500");
    });

    it("still saves to localStorage when backend save rejects (optimistic)", async () => {
      // #given a logged-in user and a backend that 500s
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      vi.mocked(api.authAPI.updatePreferences).mockRejectedValueOnce(
        new Error("HTTP 500: Internal Server Error"),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      // #when the user updates a setting
      await act(async () => {
        try {
          await result.current.mutateAsync({ theme: "dark" });
        } catch {
          // expected
        }
      });

      // #then localStorage was still updated (optimistic primary store)
      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("dark");
    });
  });

  describe("useResetSettings reset failure", () => {
    it("calls toast.error and exposes mutation.error when backend reset rejects", async () => {
      // #given a logged-in user and a backend reset that 500s
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      vi.mocked(api.authAPI.replacePreferences).mockRejectedValueOnce(
        new Error("HTTP 500: Internal Server Error"),
      );

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      // #when the user resets settings
      await act(async () => {
        try {
          await result.current.mutateAsync();
        } catch {
          // mutation should reject so consumers can chain onError
        }
      });

      // #then a toast.error is shown and mutation.error is non-null
      await waitFor(() => {
        expect(vi.mocked(toast.error)).toHaveBeenCalled();
      });
      expect(result.current.error).toBeTruthy();
    });

    it("still clears localStorage when backend reset rejects (optimistic)", async () => {
      // #given a logged-in user with stored settings and a backend that 500s
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify({ theme: "dark" }),
      );
      vi.mocked(api.authAPI.replacePreferences).mockRejectedValueOnce(
        new Error("HTTP 500: Internal Server Error"),
      );

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      // #when the user resets settings
      await act(async () => {
        try {
          await result.current.mutateAsync();
        } catch {
          // expected
        }
      });

      // #then localStorage was still cleared (optimistic primary store)
      expect(localStorage.getItem(SETTINGS_STORAGE_KEY)).toBeNull();
    });
  });

  describe("backend success path remains quiet", () => {
    it("does not call toast.error when save succeeds", async () => {
      // #given a logged-in user and a backend that succeeds
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      vi.mocked(api.authAPI.updatePreferences).mockResolvedValueOnce({
        data: {},
      } as any);

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      // #when the user updates a setting
      await act(async () => {
        await result.current.mutateAsync({ theme: "dark" });
      });

      // #then no error toast fires
      expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
      expect(result.current.error).toBeNull();
    });
  });
});
