/**
 * Tests for ThemeContext
 *
 * Tests cover:
 * - Theme provider initialization
 * - Theme toggling
 * - Color scheme switching
 * - DOM class application
 * - Settings sync
 * - Non-switchable mode
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { ThemeProvider, useTheme } from "../ThemeContext";
import * as useSettingsModule from "@/hooks/useSettings";

// Mock useSettings hook
vi.mock("@/hooks/useSettings", () => ({
  useSettings: vi.fn(),
}));

describe("ThemeContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset document classes
    document.documentElement.classList.remove("dark", "classic");
    // Default mock
    vi.mocked(useSettingsModule.useSettings).mockReturnValue({
      data: undefined,
      isLoading: true,
      isSuccess: false,
    } as any);
  });

  afterEach(() => {
    document.documentElement.classList.remove("dark", "classic");
  });

  // =====================
  // Basic Hook Tests
  // =====================
  describe("useTheme Hook", () => {
    it("should throw error when used outside ThemeProvider", () => {
      expect(() => {
        renderHook(() => useTheme());
      }).toThrow("useTheme must be used within ThemeProvider");
    });

    it("should return theme context values when used inside ThemeProvider", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBeDefined();
      expect(result.current.colorScheme).toBeDefined();
      expect(result.current.toggleTheme).toBeDefined();
      expect(result.current.setTheme).toBeDefined();
      expect(result.current.setColorScheme).toBeDefined();
      expect(result.current.switchable).toBe(true);
    });
  });

  // =====================
  // Default State Tests
  // =====================
  describe("Default State", () => {
    it("should use light theme by default", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("light");
    });

    it("should use navy color scheme by default", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.colorScheme).toBe("navy");
    });

    it("should accept custom default theme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultTheme="dark">{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("dark");
    });

    it("should accept custom default color scheme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultColorScheme="classic">{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.colorScheme).toBe("classic");
    });
  });

  // =====================
  // Theme Toggle Tests
  // =====================
  describe("Theme Toggle", () => {
    it("should toggle theme from light to dark", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("light");

      act(() => {
        result.current.toggleTheme?.();
      });

      expect(result.current.theme).toBe("dark");
    });

    it("should toggle theme from dark to light", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultTheme="dark">{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("dark");

      act(() => {
        result.current.toggleTheme?.();
      });

      expect(result.current.theme).toBe("light");
    });

    it("should apply dark class to document when dark theme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultTheme="dark">{children}</ThemeProvider>
      );

      renderHook(() => useTheme(), { wrapper });

      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should remove dark class when light theme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      renderHook(() => useTheme(), { wrapper });

      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  // =====================
  // Set Theme Tests
  // =====================
  describe("setTheme", () => {
    it("should set theme to dark", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme?.("dark");
      });

      expect(result.current.theme).toBe("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should set theme to light", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultTheme="dark">{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme?.("light");
      });

      expect(result.current.theme).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  // =====================
  // Color Scheme Tests
  // =====================
  describe("Color Scheme", () => {
    it("should set color scheme to classic", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setColorScheme?.("classic");
      });

      expect(result.current.colorScheme).toBe("classic");
      expect(document.documentElement.classList.contains("classic")).toBe(true);
    });

    it("should set color scheme to navy", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider defaultColorScheme="classic">{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setColorScheme?.("navy");
      });

      expect(result.current.colorScheme).toBe("navy");
      expect(document.documentElement.classList.contains("classic")).toBe(
        false,
      );
    });
  });

  // =====================
  // Non-Switchable Mode Tests
  // =====================
  describe("Non-Switchable Mode", () => {
    it("should not provide toggleTheme when switchable is false", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider switchable={false}>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.toggleTheme).toBeUndefined();
      expect(result.current.setTheme).toBeUndefined();
      expect(result.current.setColorScheme).toBeUndefined();
      expect(result.current.switchable).toBe(false);
    });
  });

  // =====================
  // Settings Sync Tests
  // =====================
  describe("Settings Sync", () => {
    it("should sync theme from settings when loaded", async () => {
      vi.mocked(useSettingsModule.useSettings).mockReturnValue({
        data: { theme: "dark", colorScheme: "classic" },
        isLoading: false,
        isSuccess: true,
      } as any);

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      await waitFor(() => {
        expect(result.current.theme).toBe("dark");
        expect(result.current.colorScheme).toBe("classic");
      });
    });

    it("should not sync if settings theme matches current", async () => {
      vi.mocked(useSettingsModule.useSettings).mockReturnValue({
        data: { theme: "light", colorScheme: "navy" },
        isLoading: false,
        isSuccess: true,
      } as any);

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      // Should remain at defaults since they match
      expect(result.current.theme).toBe("light");
      expect(result.current.colorScheme).toBe("navy");
    });

    it("should handle missing settings data", () => {
      vi.mocked(useSettingsModule.useSettings).mockReturnValue({
        data: undefined,
        isLoading: false,
        isSuccess: false,
      } as any);

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      // Should use defaults
      expect(result.current.theme).toBe("light");
      expect(result.current.colorScheme).toBe("navy");
    });
  });
});
