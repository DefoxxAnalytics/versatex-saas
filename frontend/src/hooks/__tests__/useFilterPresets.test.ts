/**
 * Tests for useFilterPresets hook
 *
 * Tests cover:
 * - Loading presets from localStorage
 * - Saving new presets
 * - Deleting presets
 * - Updating presets
 * - Getting presets by ID
 * - Checking name uniqueness
 * - Error handling for corrupted storage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFilterPresets, type FilterPreset } from "../useFilterPresets";
import type { Filters } from "../useFilters";

const PRESETS_KEY = "filter_presets";

// Mock filter data
const mockFilters: Filters = {
  categories: ["Office Supplies"],
  suppliers: ["Acme Corp"],
  dateRange: { start: "2024-01-01", end: "2024-12-31" },
  minAmount: 100,
  maxAmount: 10000,
  years: [2024],
  locations: ["New York"],
};

const mockPresets: FilterPreset[] = [
  {
    id: "preset_1",
    name: "Q1 Analysis",
    filters: mockFilters,
    createdAt: "2024-01-15T10:00:00Z",
  },
  {
    id: "preset_2",
    name: "Acme Only",
    filters: { ...mockFilters, suppliers: ["Acme Corp"] },
    createdAt: "2024-01-20T14:30:00Z",
  },
];

describe("useFilterPresets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // =====================
  // Loading Tests
  // =====================
  describe("Loading Presets", () => {
    it("should return empty array when no presets exist", () => {
      const { result } = renderHook(() => useFilterPresets());
      expect(result.current.presets).toEqual([]);
    });

    it("should load presets from localStorage on mount", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.presets).toEqual(mockPresets);
    });

    it("should handle corrupted localStorage data gracefully", () => {
      localStorage.setItem(PRESETS_KEY, "not valid json {{{");

      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.presets).toEqual([]);
    });

    it("should handle null localStorage value", () => {
      localStorage.setItem(PRESETS_KEY, "null");

      const { result } = renderHook(() => useFilterPresets());

      // JSON.parse('null') returns null, which gets set as-is
      // The hook returns it as null (not converted to [])
      expect(result.current.presets).toBeNull();
    });
  });

  // =====================
  // Save Preset Tests
  // =====================
  describe("savePreset", () => {
    it("should save a new preset", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("New Preset", mockFilters);
      });

      expect(result.current.presets).toHaveLength(1);
      expect(result.current.presets[0].name).toBe("New Preset");
      expect(result.current.presets[0].filters).toEqual(mockFilters);
    });

    it("should generate unique ID for new preset", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("Preset 1", mockFilters);
      });

      act(() => {
        result.current.savePreset("Preset 2", mockFilters);
      });

      expect(result.current.presets).toHaveLength(2);
      expect(result.current.presets[0].id).not.toBe(
        result.current.presets[1].id,
      );
    });

    it("should include createdAt timestamp", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("Test Preset", mockFilters);
      });

      expect(result.current.presets[0].createdAt).toBeDefined();
      // Verify it's a valid ISO date string
      const date = new Date(result.current.presets[0].createdAt);
      expect(date.getTime()).not.toBeNaN();
    });

    it("should persist to localStorage", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("Persisted Preset", mockFilters);
      });

      const stored = JSON.parse(localStorage.getItem(PRESETS_KEY) || "[]");
      expect(stored).toHaveLength(1);
      expect(stored[0].name).toBe("Persisted Preset");
    });

    it("should return the created preset", () => {
      const { result } = renderHook(() => useFilterPresets());

      let newPreset: FilterPreset | undefined;
      act(() => {
        newPreset = result.current.savePreset("Return Test", mockFilters);
      });

      expect(newPreset).toBeDefined();
      expect(newPreset?.name).toBe("Return Test");
    });

    it("should append to existing presets", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("New Third Preset", mockFilters);
      });

      expect(result.current.presets).toHaveLength(3);
    });
  });

  // =====================
  // Delete Preset Tests
  // =====================
  describe("deletePreset", () => {
    it("should delete preset by ID", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.deletePreset("preset_1");
      });

      expect(result.current.presets).toHaveLength(1);
      expect(result.current.presets[0].id).toBe("preset_2");
    });

    it("should persist deletion to localStorage", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.deletePreset("preset_1");
      });

      const stored = JSON.parse(localStorage.getItem(PRESETS_KEY) || "[]");
      expect(stored).toHaveLength(1);
    });

    it("should handle deleting non-existent ID gracefully", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.deletePreset("non-existent-id");
      });

      expect(result.current.presets).toHaveLength(2);
    });

    it("should handle deleting from empty presets", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.deletePreset("any-id");
      });

      expect(result.current.presets).toEqual([]);
    });
  });

  // =====================
  // Update Preset Tests
  // =====================
  describe("updatePreset", () => {
    it("should update preset name", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.updatePreset("preset_1", { name: "Updated Name" });
      });

      expect(result.current.presets[0].name).toBe("Updated Name");
    });

    it("should update preset filters", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      const newFilters: Filters = {
        ...mockFilters,
        categories: ["New Category"],
      };

      act(() => {
        result.current.updatePreset("preset_1", { filters: newFilters });
      });

      expect(result.current.presets[0].filters.categories).toEqual([
        "New Category",
      ]);
    });

    it("should persist updates to localStorage", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.updatePreset("preset_1", { name: "Persisted Update" });
      });

      const stored = JSON.parse(localStorage.getItem(PRESETS_KEY) || "[]");
      expect(stored[0].name).toBe("Persisted Update");
    });

    it("should not modify other presets", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.updatePreset("preset_1", { name: "Changed" });
      });

      expect(result.current.presets[1].name).toBe("Acme Only");
    });

    it("should handle updating non-existent ID gracefully", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.updatePreset("non-existent", { name: "New Name" });
      });

      // No changes should occur
      expect(result.current.presets).toHaveLength(2);
      expect(result.current.presets[0].name).toBe("Q1 Analysis");
    });
  });

  // =====================
  // Get Preset Tests
  // =====================
  describe("getPreset", () => {
    it("should return preset by ID", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      const preset = result.current.getPreset("preset_1");

      expect(preset).toBeDefined();
      expect(preset?.name).toBe("Q1 Analysis");
    });

    it("should return undefined for non-existent ID", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      const preset = result.current.getPreset("non-existent");

      expect(preset).toBeUndefined();
    });

    it("should return undefined when no presets exist", () => {
      const { result } = renderHook(() => useFilterPresets());

      const preset = result.current.getPreset("any-id");

      expect(preset).toBeUndefined();
    });
  });

  // =====================
  // Name Exists Tests
  // =====================
  describe("nameExists", () => {
    it("should return true if name exists", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.nameExists("Q1 Analysis")).toBe(true);
    });

    it("should return false if name does not exist", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.nameExists("Non Existent Name")).toBe(false);
    });

    it("should check case-insensitively", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.nameExists("q1 analysis")).toBe(true);
      expect(result.current.nameExists("Q1 ANALYSIS")).toBe(true);
    });

    it("should exclude specific ID from check", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      // Should return false because we're excluding preset_1 which has the name
      expect(result.current.nameExists("Q1 Analysis", "preset_1")).toBe(false);
    });

    it("should still detect conflict when excluding different ID", () => {
      localStorage.setItem(PRESETS_KEY, JSON.stringify(mockPresets));

      const { result } = renderHook(() => useFilterPresets());

      // Should return true because preset_1 has the name and we're excluding preset_2
      expect(result.current.nameExists("Q1 Analysis", "preset_2")).toBe(true);
    });

    it("should return false when no presets exist", () => {
      const { result } = renderHook(() => useFilterPresets());

      expect(result.current.nameExists("Any Name")).toBe(false);
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle empty string name", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("", mockFilters);
      });

      expect(result.current.presets[0].name).toBe("");
    });

    it("should handle filters with empty arrays", () => {
      const emptyFilters: Filters = {
        categories: [],
        suppliers: [],
        dateRange: { start: null, end: null },
        minAmount: null,
        maxAmount: null,
        years: [],
        locations: [],
      };

      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("Empty Filters", emptyFilters);
      });

      expect(result.current.presets[0].filters).toEqual(emptyFilters);
    });

    it("should handle special characters in preset name", () => {
      const { result } = renderHook(() => useFilterPresets());

      const specialName = 'Test: "Special" <Characters> & More!';

      act(() => {
        result.current.savePreset(specialName, mockFilters);
      });

      expect(result.current.presets[0].name).toBe(specialName);
    });

    it("should handle sequential saves", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        result.current.savePreset("Preset 1", mockFilters);
      });
      act(() => {
        result.current.savePreset("Preset 2", mockFilters);
      });
      act(() => {
        result.current.savePreset("Preset 3", mockFilters);
      });

      expect(result.current.presets).toHaveLength(3);
    });

    it("should handle save and delete in sequence", () => {
      const { result } = renderHook(() => useFilterPresets());

      act(() => {
        const preset = result.current.savePreset("Temp Preset", mockFilters);
        result.current.deletePreset(preset.id);
      });

      expect(result.current.presets).toHaveLength(0);
    });
  });
});
