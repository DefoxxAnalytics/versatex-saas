/**
 * Tests for useComposition hook
 *
 * Tests cover:
 * - Composition event handling for IME input
 * - Key event blocking during composition
 * - Timer cleanup
 * - Custom callbacks
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useComposition } from "../useComposition";

describe("useComposition", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  // =====================
  // Basic Hook Tests
  // =====================
  describe("Basic Hook", () => {
    it("should return composition handlers", () => {
      const { result } = renderHook(() => useComposition());

      expect(result.current.onCompositionStart).toBeDefined();
      expect(result.current.onCompositionEnd).toBeDefined();
      expect(result.current.onKeyDown).toBeDefined();
      expect(result.current.isComposing).toBeDefined();
    });

    it("should initially not be composing", () => {
      const { result } = renderHook(() => useComposition());

      expect(result.current.isComposing()).toBe(false);
    });
  });

  // =====================
  // Composition Start Tests
  // =====================
  describe("onCompositionStart", () => {
    it("should set composing to true", () => {
      const { result } = renderHook(() => useComposition());

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
      });

      expect(result.current.isComposing()).toBe(true);
    });

    it("should call original onCompositionStart if provided", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onCompositionStart: originalHandler }),
      );

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
      });

      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should clear existing timers when composition starts", () => {
      const { result } = renderHook(() => useComposition());

      // Start and end composition to set timers
      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
        result.current.onCompositionEnd(mockEvent);
      });

      // Start composition again to clear timers
      act(() => {
        result.current.onCompositionStart(mockEvent);
      });

      // Should still be composing (timers were cleared)
      expect(result.current.isComposing()).toBe(true);
    });
  });

  // =====================
  // Composition End Tests
  // =====================
  describe("onCompositionEnd", () => {
    it("should set composing to false after timeout", () => {
      const { result } = renderHook(() => useComposition());

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
      });

      expect(result.current.isComposing()).toBe(true);

      act(() => {
        result.current.onCompositionEnd(mockEvent);
      });

      // Still composing immediately after end
      expect(result.current.isComposing()).toBe(true);

      // Run all timers
      act(() => {
        vi.runAllTimers();
      });

      expect(result.current.isComposing()).toBe(false);
    });

    it("should call original onCompositionEnd if provided", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onCompositionEnd: originalHandler }),
      );

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionEnd(mockEvent);
      });

      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });
  });

  // =====================
  // Key Down Tests
  // =====================
  describe("onKeyDown", () => {
    it("should block Escape key during composition", () => {
      const { result } = renderHook(() => useComposition());

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "Escape",
        shiftKey: false,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Start composition
      act(() => {
        result.current.onCompositionStart(
          {} as React.CompositionEvent<HTMLInputElement>,
        );
      });

      // Escape during composition
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).toHaveBeenCalled();
    });

    it("should block Enter key during composition", () => {
      const { result } = renderHook(() => useComposition());

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "Enter",
        shiftKey: false,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Start composition
      act(() => {
        result.current.onCompositionStart(
          {} as React.CompositionEvent<HTMLInputElement>,
        );
      });

      // Enter during composition
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).toHaveBeenCalled();
    });

    it("should allow Shift+Enter during composition", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onKeyDown: originalHandler }),
      );

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "Enter",
        shiftKey: true,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Start composition
      act(() => {
        result.current.onCompositionStart(
          {} as React.CompositionEvent<HTMLInputElement>,
        );
      });

      // Shift+Enter during composition
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).not.toHaveBeenCalled();
      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should allow other keys during composition", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onKeyDown: originalHandler }),
      );

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "a",
        shiftKey: false,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Start composition
      act(() => {
        result.current.onCompositionStart(
          {} as React.CompositionEvent<HTMLInputElement>,
        );
      });

      // Regular key during composition
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).not.toHaveBeenCalled();
      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should allow Enter key when not composing", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onKeyDown: originalHandler }),
      );

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "Enter",
        shiftKey: false,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Not composing, Enter should be allowed
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).not.toHaveBeenCalled();
      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should allow Escape key when not composing", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onKeyDown: originalHandler }),
      );

      const mockStopPropagation = vi.fn();
      const mockEvent = {
        key: "Escape",
        shiftKey: false,
        stopPropagation: mockStopPropagation,
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      // Not composing, Escape should be allowed
      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(mockStopPropagation).not.toHaveBeenCalled();
      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });

    it("should call original onKeyDown if provided", () => {
      const originalHandler = vi.fn();
      const { result } = renderHook(() =>
        useComposition({ onKeyDown: originalHandler }),
      );

      const mockEvent = {
        key: "a",
        shiftKey: false,
        stopPropagation: vi.fn(),
      } as unknown as React.KeyboardEvent<HTMLInputElement>;

      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(originalHandler).toHaveBeenCalledWith(mockEvent);
    });
  });

  // =====================
  // TextArea Type Tests
  // =====================
  describe("TextArea Support", () => {
    it("should work with HTMLTextAreaElement type", () => {
      const { result } = renderHook(() =>
        useComposition<HTMLTextAreaElement>(),
      );

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLTextAreaElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
      });

      expect(result.current.isComposing()).toBe(true);
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle rapid composition start/end cycles", () => {
      const { result } = renderHook(() => useComposition());

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      // Rapid cycles
      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.onCompositionStart(mockEvent);
          result.current.onCompositionEnd(mockEvent);
        });
      }

      // Should still be in expected state after all timers
      act(() => {
        vi.runAllTimers();
      });

      expect(result.current.isComposing()).toBe(false);
    });

    it("should handle composition end before start has finished", () => {
      const { result } = renderHook(() => useComposition());

      const mockEvent = {
        data: "test",
      } as React.CompositionEvent<HTMLInputElement>;

      act(() => {
        result.current.onCompositionStart(mockEvent);
        // End immediately
        result.current.onCompositionEnd(mockEvent);
        // Start again (should clear timers from end)
        result.current.onCompositionStart(mockEvent);
      });

      expect(result.current.isComposing()).toBe(true);
    });
  });
});
