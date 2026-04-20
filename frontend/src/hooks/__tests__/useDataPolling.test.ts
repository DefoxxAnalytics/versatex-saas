/**
 * Tests for useDataPolling hook
 *
 * Tests cover:
 * - Polling state management
 * - Start/stop polling
 * - New data detection
 * - Toast notifications
 * - Custom callbacks
 * - Event handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useDataPolling } from "../useDataPolling";
import * as api from "@/lib/api";
import * as sonner from "sonner";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  procurementAPI: {
    getTransactions: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
  },
}));

describe("useDataPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    // Default mock return
    vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
      data: { count: 100, results: [] },
    } as any);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // =====================
  // Initial State Tests
  // =====================
  describe("Initial State", () => {
    it("should initialize with correct default state", () => {
      const { result } = renderHook(() => useDataPolling({ enabled: false }));

      expect(result.current.isPolling).toBe(false);
      expect(result.current.lastCount).toBeNull();
      expect(result.current.hasNewData).toBe(false);
      expect(result.current.lastChecked).toBeNull();
    });

    it("should return control functions", () => {
      const { result } = renderHook(() => useDataPolling({ enabled: false }));

      expect(typeof result.current.startPolling).toBe("function");
      expect(typeof result.current.stopPolling).toBe("function");
      expect(typeof result.current.checkForNewData).toBe("function");
      expect(typeof result.current.clearNewDataFlag).toBe("function");
    });
  });

  // =====================
  // Polling Control Tests
  // =====================
  describe("Polling Control", () => {
    it("should start polling when enabled", async () => {
      renderHook(() => useDataPolling({ enabled: true, interval: 10000 }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledWith({
        page_size: 1,
      });
    });

    it("should not start polling when disabled", () => {
      const { result } = renderHook(() => useDataPolling({ enabled: false }));

      expect(result.current.isPolling).toBe(false);
      expect(api.procurementAPI.getTransactions).not.toHaveBeenCalled();
    });

    it("should start polling manually", async () => {
      const { result } = renderHook(() => useDataPolling({ enabled: false }));

      await act(async () => {
        result.current.startPolling();
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.isPolling).toBe(true);
      expect(api.procurementAPI.getTransactions).toHaveBeenCalled();
    });

    it("should stop polling manually", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 10000 }),
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      act(() => {
        result.current.stopPolling();
      });

      expect(result.current.isPolling).toBe(false);
    });

    it("should not start polling multiple times", async () => {
      const { result } = renderHook(() => useDataPolling({ enabled: false }));

      await act(async () => {
        result.current.startPolling();
        result.current.startPolling();
        result.current.startPolling();
        await vi.advanceTimersByTimeAsync(0);
      });

      // Should only have made one initial call
      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);
    });
  });

  // =====================
  // Data Check Tests
  // =====================
  describe("Data Checking", () => {
    it("should store initial count on first check", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 10000 }),
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.lastCount).toBe(100);
      expect(result.current.lastChecked).toBeTruthy();
    });

    it("should detect new data when count increases", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Update mock to return more records
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { count: 105, results: [] },
      } as any);

      // Second check after interval
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.lastCount).toBe(105);
      expect(result.current.hasNewData).toBe(true);
      expect(sonner.toast.info).toHaveBeenCalled();
    });

    it("should detect data change when count decreases", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Update mock to return fewer records
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { count: 90, results: [] },
      } as any);

      // Second check after interval
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.lastCount).toBe(90);
      expect(result.current.hasNewData).toBe(true);
    });

    it("should not flag new data when count unchanged", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Second check with same count
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.hasNewData).toBe(false);
    });
  });

  // =====================
  // Callback Tests
  // =====================
  describe("Callbacks", () => {
    it("should call onNewData callback when data changes", async () => {
      const onNewData = vi.fn();
      renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000, onNewData }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Update mock
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { count: 110, results: [] },
      } as any);

      // Second check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(onNewData).toHaveBeenCalledWith(110, 100);
    });
  });

  // =====================
  // Clear Flag Tests
  // =====================
  describe("Clear New Data Flag", () => {
    it("should clear hasNewData flag", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Trigger new data
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { count: 105, results: [] },
      } as any);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(result.current.hasNewData).toBe(true);

      // Clear flag
      act(() => {
        result.current.clearNewDataFlag();
      });

      expect(result.current.hasNewData).toBe(false);
    });
  });

  // =====================
  // Polling Interval Tests
  // =====================
  describe("Polling Interval", () => {
    it("should use custom interval", async () => {
      renderHook(() => useDataPolling({ enabled: true, interval: 5000 }));

      // Initial check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);

      // Not enough time
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);

      // After full interval
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(2);
    });

    it("should use default 60 second interval", async () => {
      renderHook(() => useDataPolling({ enabled: true }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);

      // After 30 seconds
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);

      // After 60 seconds total
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(2);
    });
  });

  // =====================
  // Error Handling Tests
  // =====================
  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      vi.mocked(api.procurementAPI.getTransactions).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      // Should not throw
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // State should remain unchanged
      expect(result.current.lastCount).toBeNull();
      expect(result.current.isPolling).toBe(true);
    });

    it("should continue polling after error", async () => {
      vi.mocked(api.procurementAPI.getTransactions)
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce({ data: { count: 100, results: [] } } as any);

      renderHook(() => useDataPolling({ enabled: true, interval: 1000 }));

      // First check fails
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Second check succeeds
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(2);
    });
  });

  // =====================
  // Cleanup Tests
  // =====================
  describe("Cleanup", () => {
    it("should stop polling on unmount", async () => {
      const { unmount } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 1000 }),
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);

      unmount();

      // After unmount, no more calls should happen
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(api.procurementAPI.getTransactions).toHaveBeenCalledTimes(1);
    });
  });

  // =====================
  // Event Listener Tests
  // =====================
  describe("Event Listeners", () => {
    it("should respond to refreshData event", async () => {
      const { result } = renderHook(() =>
        useDataPolling({ enabled: true, interval: 10000 }),
      );

      // First check
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Trigger new data
      vi.mocked(api.procurementAPI.getTransactions).mockResolvedValue({
        data: { count: 110, results: [] },
      } as any);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });

      expect(result.current.hasNewData).toBe(true);

      // Dispatch refresh event
      await act(async () => {
        window.dispatchEvent(new CustomEvent("refreshData"));
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.hasNewData).toBe(false);
    });
  });
});
