/**
 * Tests for useSettings hooks
 *
 * Tests cover:
 * - Loading settings from localStorage
 * - Backend sync on mount
 * - Updating settings
 * - Resetting to defaults
 * - Theme and color scheme validation
 * - AI settings validation
 * - Export format validation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useSettings,
  useUpdateSettings,
  useResetSettings,
  type UserSettings,
} from "../useSettings";
import * as api from "@/lib/api";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  authAPI: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
    replacePreferences: vi.fn(),
  },
}));

const SETTINGS_STORAGE_KEY = "user-settings";
const USER_KEY = "user";

const defaultSettings: UserSettings = {
  theme: "light",
  colorScheme: "navy",
  notifications: true,
  exportFormat: "csv",
  currency: "USD",
  dateFormat: "MM/DD/YYYY",
  timezone: "America/New_York",
  forecastingModel: "standard",
  useExternalAI: false,
  aiProvider: "anthropic",
  forecastHorizonMonths: 6,
  anomalySensitivity: 2,
};

const customSettings: UserSettings = {
  theme: "dark",
  colorScheme: "classic",
  notifications: false,
  exportFormat: "xlsx",
  currency: "EUR",
  dateFormat: "DD/MM/YYYY",
  timezone: "Europe/London",
  forecastingModel: "simple",
  useExternalAI: true,
  aiProvider: "openai",
  forecastHorizonMonths: 12,
  anomalySensitivity: 4,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useSettings Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // =====================
  // useSettings Tests
  // =====================
  describe("useSettings", () => {
    it("should return default settings when no stored settings", async () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.theme).toBe("light");
      expect(result.current.data?.colorScheme).toBe("navy");
      expect(result.current.data?.notifications).toBe(true);
    });

    it("should load settings from localStorage", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(customSettings),
      );

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.theme).toBe("dark");
      expect(result.current.data?.colorScheme).toBe("classic");
    });

    it("should merge stored settings with defaults", async () => {
      // Store partial settings
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify({ theme: "dark" }),
      );

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.theme).toBe("dark");
      // Other settings should be defaults
      expect(result.current.data?.colorScheme).toBe("navy");
    });

    it("should handle corrupted localStorage data gracefully", async () => {
      localStorage.setItem(SETTINGS_STORAGE_KEY, "not valid json");

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should return defaults
      expect(result.current.data?.theme).toBe("light");
    });

    it("should sync with backend when authenticated", async () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      vi.mocked(api.authAPI.getPreferences).mockResolvedValue({
        data: { theme: "dark", colorScheme: "classic" },
      } as any);

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Wait for backend sync effect
      await waitFor(() => {
        expect(api.authAPI.getPreferences).toHaveBeenCalled();
      });
    });

    it("should not sync with backend when not authenticated", async () => {
      // No user in localStorage

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Small delay to ensure effect ran
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(api.authAPI.getPreferences).not.toHaveBeenCalled();
    });
  });

  // =====================
  // useUpdateSettings Tests
  // =====================
  describe("useUpdateSettings", () => {
    it("should update theme setting", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ theme: "dark" });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("dark");
    });

    it("should update color scheme", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ colorScheme: "classic" });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.colorScheme).toBe("classic");
    });

    it("should update notifications setting", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ notifications: false });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.notifications).toBe(false);
    });

    it("should update export format", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ exportFormat: "pdf" });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.exportFormat).toBe("pdf");
    });

    it("should validate and fix invalid theme value", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ theme: "invalid" as any });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("light"); // Reset to default
    });

    it("should validate and fix invalid color scheme", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ colorScheme: "invalid" as any });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.colorScheme).toBe("navy"); // Reset to default
    });

    it("should validate and fix invalid export format", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ exportFormat: "invalid" as any });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.exportFormat).toBe("csv"); // Reset to default
    });

    it("should update AI settings", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({
          forecastingModel: "simple",
          useExternalAI: true,
          aiProvider: "openai",
        });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.forecastingModel).toBe("simple");
      expect(stored.useExternalAI).toBe(true);
      expect(stored.aiProvider).toBe("openai");
    });

    it("should clamp forecast horizon to valid range", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ forecastHorizonMonths: 100 });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.forecastHorizonMonths).toBe(24); // Max is 24
    });

    it("should clamp forecast horizon minimum", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ forecastHorizonMonths: 1 });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.forecastHorizonMonths).toBe(3); // Min is 3
    });

    it("should clamp anomaly sensitivity to valid range", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ anomalySensitivity: 10 });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.anomalySensitivity).toBe(5); // Max is 5
    });

    it("should sync to backend when authenticated", async () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );
      vi.mocked(api.authAPI.updatePreferences).mockResolvedValue({
        data: {},
      } as any);

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ theme: "dark" });
      });

      expect(api.authAPI.updatePreferences).toHaveBeenCalled();
    });

    it("should not fail if backend sync fails", async () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );
      vi.mocked(api.authAPI.updatePreferences).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ theme: "dark" });
      });

      // Should still succeed locally
      expect(result.current.isSuccess).toBe(true);
      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("dark");
    });

    it("should update multiple settings at once", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({
          theme: "dark",
          colorScheme: "classic",
          notifications: false,
        });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("dark");
      expect(stored.colorScheme).toBe("classic");
      expect(stored.notifications).toBe(false);
    });
  });

  // =====================
  // useResetSettings Tests
  // =====================
  describe("useResetSettings", () => {
    it("should reset settings to defaults", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(customSettings),
      );

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync();
      });

      // localStorage should be cleared
      expect(localStorage.getItem(SETTINGS_STORAGE_KEY)).toBeNull();
    });

    it("should return default settings after reset", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(customSettings),
      );

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      let resetData: UserSettings | undefined;
      await act(async () => {
        resetData = await result.current.mutateAsync();
      });

      expect(resetData?.theme).toBe("light");
      expect(resetData?.colorScheme).toBe("navy");
    });

    it("should sync reset to backend when authenticated", async () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(customSettings),
      );
      vi.mocked(api.authAPI.replacePreferences).mockResolvedValue({
        data: {},
      } as any);

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync();
      });

      expect(api.authAPI.replacePreferences).toHaveBeenCalledWith({});
    });

    it("should not fail if backend sync fails on reset", async () => {
      localStorage.setItem(USER_KEY, JSON.stringify({ id: 1 }));
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(customSettings),
      );
      vi.mocked(api.authAPI.replacePreferences).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useResetSettings(), {
        wrapper: createWrapper(),
      });

      // Should complete without throwing even if backend fails
      let didComplete = false;
      let returnedSettings: UserSettings | undefined;
      await act(async () => {
        returnedSettings = await result.current.mutateAsync();
        didComplete = true;
      });

      // Mutation should complete successfully (error is caught internally)
      expect(didComplete).toBe(true);
      // Should return default settings
      expect(returnedSettings?.theme).toBe("light");
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle empty localStorage gracefully", async () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toBeDefined();
    });

    it("should handle rapid setting updates", async () => {
      localStorage.setItem(
        SETTINGS_STORAGE_KEY,
        JSON.stringify(defaultSettings),
      );

      const { result } = renderHook(() => useUpdateSettings(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ theme: "dark" });
        await result.current.mutateAsync({ theme: "light" });
        await result.current.mutateAsync({ theme: "dark" });
      });

      const stored = JSON.parse(
        localStorage.getItem(SETTINGS_STORAGE_KEY) || "{}",
      );
      expect(stored.theme).toBe("dark");
    });
  });
});
