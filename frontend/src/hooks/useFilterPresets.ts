/**
 * useFilterPresets Hook
 *
 * Manages saved filter presets in localStorage.
 * Allows users to save, load, and delete filter combinations.
 */

import { useState, useEffect, useCallback } from "react";
import type { Filters } from "./useFilters";

const PRESETS_KEY = "filter_presets";

/**
 * Filter preset structure
 */
export interface FilterPreset {
  id: string;
  name: string;
  filters: Filters;
  createdAt: string;
}

/**
 * Generate a unique ID for presets
 */
function generateId(): string {
  return `preset_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Load presets from localStorage
 */
function loadPresets(): FilterPreset[] {
  try {
    const stored = localStorage.getItem(PRESETS_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as FilterPreset[];
  } catch (error) {
    // Only log in development
    if (import.meta.env.DEV) {
      console.error("Failed to load filter presets:", error);
    }
    return [];
  }
}

/**
 * Save presets to localStorage
 */
function savePresets(presets: FilterPreset[]): void {
  try {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
  } catch (error) {
    // Only log in development
    if (import.meta.env.DEV) {
      console.error("Failed to save filter presets:", error);
    }
  }
}

/**
 * Hook for managing filter presets
 */
export function useFilterPresets() {
  const [presets, setPresets] = useState<FilterPreset[]>([]);

  // Load presets on mount
  useEffect(() => {
    setPresets(loadPresets());
  }, []);

  /**
   * Save a new preset
   */
  const savePreset = useCallback(
    (name: string, filters: Filters): FilterPreset => {
      const newPreset: FilterPreset = {
        id: generateId(),
        name,
        filters,
        createdAt: new Date().toISOString(),
      };

      const updated = [...presets, newPreset];
      setPresets(updated);
      savePresets(updated);

      return newPreset;
    },
    [presets],
  );

  /**
   * Delete a preset by ID
   */
  const deletePreset = useCallback(
    (id: string): void => {
      const updated = presets.filter((p) => p.id !== id);
      setPresets(updated);
      savePresets(updated);
    },
    [presets],
  );

  /**
   * Update an existing preset
   */
  const updatePreset = useCallback(
    (
      id: string,
      updates: Partial<Pick<FilterPreset, "name" | "filters">>,
    ): void => {
      const updated = presets.map((p) =>
        p.id === id ? { ...p, ...updates } : p,
      );
      setPresets(updated);
      savePresets(updated);
    },
    [presets],
  );

  /**
   * Get a preset by ID
   */
  const getPreset = useCallback(
    (id: string): FilterPreset | undefined => {
      return presets.find((p) => p.id === id);
    },
    [presets],
  );

  /**
   * Check if a preset name already exists
   */
  const nameExists = useCallback(
    (name: string, excludeId?: string): boolean => {
      return presets.some(
        (p) =>
          p.name.toLowerCase() === name.toLowerCase() && p.id !== excludeId,
      );
    },
    [presets],
  );

  return {
    presets,
    savePreset,
    deletePreset,
    updatePreset,
    getPreset,
    nameExists,
  };
}
