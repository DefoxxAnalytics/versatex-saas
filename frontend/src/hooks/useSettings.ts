import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { authAPI, type UserPreferences } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

/**
 * Color scheme type for brand theming
 * - navy: New navy blue & white theme (default)
 * - classic: Original light theme with white header/sidebar
 * - versatex: Official Versatex brand — grayscale chrome with yellow accent
 */
export type ColorScheme = "navy" | "classic" | "versatex";

/**
 * AI Provider type
 */
export type AIProvider = "anthropic" | "openai";

/**
 * Forecasting model type
 */
export type ForecastingModel = "simple" | "standard";

/**
 * User settings interface
 * Defines all configurable user preferences
 */
export interface UserSettings {
  // Theme preferences
  theme: "light" | "dark";

  // Color scheme (brand theme)
  colorScheme: ColorScheme;

  // Notification settings
  notifications: boolean;

  // Export preferences
  exportFormat: "csv" | "xlsx" | "pdf";

  // User profile
  userName?: string;
  userEmail?: string;
  userRole?: string;

  // Display preferences
  currency?: string;
  dateFormat?: string;
  timezone?: string;

  // AI & Predictive Analytics Settings
  forecastingModel: ForecastingModel;
  useExternalAI: boolean;
  aiProvider: AIProvider;
  aiApiKey?: string; // Stored encrypted, never displayed
  forecastHorizonMonths: number;
  anomalySensitivity: number;
}

/**
 * Default settings
 * Used when no saved settings exist
 */
const DEFAULT_SETTINGS: UserSettings = {
  theme: "light",
  colorScheme: "navy",
  notifications: true,
  exportFormat: "csv",
  currency: "USD",
  dateFormat: "MM/DD/YYYY",
  timezone: "America/New_York",
  // AI & Predictive Analytics defaults
  forecastingModel: "standard",
  useExternalAI: false,
  aiProvider: "anthropic",
  forecastHorizonMonths: 6,
  anomalySensitivity: 2,
};

/**
 * LocalStorage key for settings persistence
 */
const SETTINGS_STORAGE_KEY = "user-settings";

/**
 * Load settings from localStorage
 * Returns default settings if none exist or if data is corrupted
 *
 * @returns User settings object
 */
function loadSettingsFromStorage(): UserSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!stored) {
      return DEFAULT_SETTINGS;
    }

    const parsed = JSON.parse(stored);

    // Merge with defaults to ensure all fields exist
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
    };
  } catch (error) {
    // Handle corrupted data - only log in development
    if (import.meta.env.DEV) {
      console.warn("Failed to load settings, using defaults:", error);
    }
    return DEFAULT_SETTINGS;
  }
}

/**
 * Save settings to localStorage
 *
 * @param settings - Settings object to save
 */
function saveSettingsToStorage(settings: Partial<UserSettings>): UserSettings {
  try {
    const current = loadSettingsFromStorage();
    const updated = { ...current, ...settings };

    // Validate theme
    if (settings.theme && !["light", "dark"].includes(settings.theme)) {
      updated.theme = DEFAULT_SETTINGS.theme;
    }

    // Validate color scheme
    if (
      settings.colorScheme &&
      !["navy", "classic", "versatex"].includes(settings.colorScheme)
    ) {
      updated.colorScheme = DEFAULT_SETTINGS.colorScheme;
    }

    // Validate export format
    if (
      settings.exportFormat &&
      !["csv", "xlsx", "pdf"].includes(settings.exportFormat)
    ) {
      updated.exportFormat = DEFAULT_SETTINGS.exportFormat;
    }

    // Validate AI settings
    if (
      settings.forecastingModel &&
      !["simple", "standard"].includes(settings.forecastingModel)
    ) {
      updated.forecastingModel = DEFAULT_SETTINGS.forecastingModel;
    }
    if (
      settings.aiProvider &&
      !["anthropic", "openai"].includes(settings.aiProvider)
    ) {
      updated.aiProvider = DEFAULT_SETTINGS.aiProvider;
    }
    if (settings.forecastHorizonMonths !== undefined) {
      updated.forecastHorizonMonths = Math.max(
        3,
        Math.min(24, settings.forecastHorizonMonths),
      );
    }
    if (settings.anomalySensitivity !== undefined) {
      updated.anomalySensitivity = Math.max(
        1,
        Math.min(5, settings.anomalySensitivity),
      );
    }

    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch (error) {
    // Only log in development
    if (import.meta.env.DEV) {
      console.error("Failed to save settings:", error);
    }
    throw error;
  }
}

/**
 * Convert UserSettings to UserPreferences (API format)
 */
function toApiFormat(
  settings: Partial<UserSettings>,
): Partial<UserPreferences> {
  const prefs: Partial<UserPreferences> = {};

  if (settings.theme !== undefined) prefs.theme = settings.theme;
  if (settings.colorScheme !== undefined)
    prefs.colorScheme = settings.colorScheme;
  if (settings.notifications !== undefined)
    prefs.notifications = settings.notifications;
  if (settings.exportFormat !== undefined)
    prefs.exportFormat = settings.exportFormat;
  if (settings.currency !== undefined) prefs.currency = settings.currency;
  if (settings.dateFormat !== undefined) prefs.dateFormat = settings.dateFormat;
  // AI settings
  if (settings.forecastingModel !== undefined)
    prefs.forecastingModel = settings.forecastingModel;
  if (settings.useExternalAI !== undefined)
    prefs.useExternalAI = settings.useExternalAI;
  if (settings.aiProvider !== undefined) prefs.aiProvider = settings.aiProvider;
  if (settings.forecastHorizonMonths !== undefined)
    prefs.forecastHorizonMonths = settings.forecastHorizonMonths;
  if (settings.anomalySensitivity !== undefined)
    prefs.anomalySensitivity = settings.anomalySensitivity;
  // Note: aiApiKey is handled separately for security (encrypted on backend)

  return prefs;
}

/**
 * Convert UserPreferences (API format) to UserSettings
 */
function fromApiFormat(prefs: UserPreferences): Partial<UserSettings> {
  const settings: Partial<UserSettings> = {};

  if (prefs.theme !== undefined && prefs.theme !== "system") {
    settings.theme = prefs.theme as "light" | "dark";
  }
  if (prefs.colorScheme !== undefined) settings.colorScheme = prefs.colorScheme;
  if (prefs.notifications !== undefined)
    settings.notifications = prefs.notifications;
  if (prefs.exportFormat !== undefined)
    settings.exportFormat = prefs.exportFormat;
  if (prefs.currency !== undefined) settings.currency = prefs.currency;
  if (prefs.dateFormat !== undefined) settings.dateFormat = prefs.dateFormat;
  // AI settings
  if (prefs.forecastingModel !== undefined)
    settings.forecastingModel = prefs.forecastingModel as "simple" | "standard";
  if (prefs.useExternalAI !== undefined)
    settings.useExternalAI = prefs.useExternalAI;
  if (prefs.aiProvider !== undefined)
    settings.aiProvider = prefs.aiProvider as "anthropic" | "openai";
  if (prefs.forecastHorizonMonths !== undefined)
    settings.forecastHorizonMonths = prefs.forecastHorizonMonths;
  if (prefs.anomalySensitivity !== undefined)
    settings.anomalySensitivity = prefs.anomalySensitivity;

  return settings;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated(): boolean {
  return localStorage.getItem("user") !== null;
}

/**
 * Hook to access user settings with backend sync
 *
 * Features:
 * - Loads settings from localStorage first (fast)
 * - Syncs with backend API when authenticated
 * - Falls back to localStorage when offline/unauthenticated
 * - Caches settings for performance
 *
 * @example
 * ```tsx
 * const { data: settings, isLoading } = useSettings();
 *
 * if (isLoading) return <div>Loading...</div>;
 *
 * return <div>Theme: {settings.theme}</div>;
 * ```
 */
export function useSettings() {
  const hasSyncedRef = useRef(false);
  const queryClient = useQueryClient();

  // Main query - loads from localStorage immediately
  const query = useQuery<UserSettings, Error>({
    queryKey: queryKeys.settings.all,
    queryFn: (): UserSettings => loadSettingsFromStorage(),
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  // Sync with backend on mount (only once per session)
  useEffect(() => {
    if (hasSyncedRef.current || !isAuthenticated()) return;
    hasSyncedRef.current = true;

    // Fetch preferences from backend and merge with local
    authAPI
      .getPreferences()
      .then((response) => {
        const apiSettings = fromApiFormat(response.data);
        const localSettings = loadSettingsFromStorage();

        // Merge: API settings take precedence over local
        const merged = { ...localSettings, ...apiSettings };

        // Save to localStorage and update cache
        saveSettingsToStorage(merged);
        queryClient.setQueryData(queryKeys.settings.all, merged);
      })
      .catch((error) => {
        // Silently fail - use local settings
        console.debug("Could not sync settings from backend:", error);
      });
  }, [queryClient]);

  return query;
}

/**
 * Hook to update user settings with backend sync
 *
 * Features:
 * - Updates localStorage immediately (optimistic)
 * - Syncs to backend API when authenticated
 * - Supports partial updates
 *
 * @example
 * ```tsx
 * const updateSettings = useUpdateSettings();
 *
 * // Update theme only
 * updateSettings.mutate({ theme: 'dark' });
 * ```
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation<UserSettings, Error, Partial<UserSettings>>({
    mutationFn: async (settings: Partial<UserSettings>) => {
      // Save to localStorage immediately
      const updated = saveSettingsToStorage(settings);

      // Sync to backend if authenticated
      if (isAuthenticated()) {
        try {
          await authAPI.updatePreferences(toApiFormat(settings));
        } catch (error) {
          // Log but don't fail - localStorage is primary
          console.debug("Could not sync settings to backend:", error);
        }
      }

      return updated;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.settings.all, data);
    },
  });
}

/**
 * Hook to reset settings to defaults
 *
 * @example
 * ```tsx
 * const resetSettings = useResetSettings();
 *
 * resetSettings.mutate();
 * ```
 */
export function useResetSettings() {
  const queryClient = useQueryClient();

  return useMutation<UserSettings, Error, void>({
    mutationFn: async () => {
      // Clear localStorage
      localStorage.removeItem(SETTINGS_STORAGE_KEY);

      // Sync to backend if authenticated
      if (isAuthenticated()) {
        try {
          await authAPI.replacePreferences({});
        } catch (error) {
          console.debug("Could not reset settings on backend:", error);
        }
      }

      return DEFAULT_SETTINGS;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.settings.all, data);
    },
  });
}
