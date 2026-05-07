import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { authAPI, type UserPreferences } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
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
 * Forecasting model type.
 *
 * Values mirror the backend ChoiceField at
 * `backend/apps/authentication/serializers.py:84-87`. Any divergence
 * causes a 400 on save and the setting silently fails to persist
 * (Finding #16). Keep the two sides in lock-step.
 */
export type ForecastingModel = "simple_average" | "linear" | "advanced";

/**
 * Source-of-truth list for the legal forecasting model values. Exported
 * so tests can assert it stays in sync with the backend serializer.
 */
export const VALID_FORECASTING_MODELS = [
  "simple_average",
  "linear",
  "advanced",
] as const satisfies readonly ForecastingModel[];

/**
 * Type guard for forecasting model values. Use this anywhere a value
 * coming from user input, localStorage, or the API needs to be narrowed
 * to `ForecastingModel` before sending it back to the backend.
 */
export function isValidForecastingModel(
  value: unknown,
): value is ForecastingModel {
  return (
    typeof value === "string" &&
    (VALID_FORECASTING_MODELS as readonly string[]).includes(value)
  );
}

/**
 * Human-readable labels for each forecasting model. Used in the
 * Settings UI Select and in toast confirmations.
 */
export const FORECASTING_MODEL_LABELS: Record<ForecastingModel, string> = {
  simple_average: "Simple Average",
  linear: "Linear Regression",
  advanced: "Advanced (ML)",
};

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
  // API key is sent to backend on save; read-back is masked ('****' + last4).
  aiApiKey?: string;
  forecastHorizonMonths: number;
  anomalySensitivity: number;
}

/**
 * Default settings.
 *
 * Used when no saved settings exist. Exported so tests can assert
 * defaults stay aligned with backend ChoiceField constraints.
 *
 * `forecastingModel` defaults to `simple_average` -- the most
 * conservative of the three backend-supported algorithms.
 */
export const DEFAULT_SETTINGS: UserSettings = {
  theme: "light",
  colorScheme: "navy",
  notifications: true,
  exportFormat: "csv",
  currency: "USD",
  dateFormat: "MM/DD/YYYY",
  timezone: "America/New_York",
  // AI & Predictive Analytics defaults
  forecastingModel: "simple_average",
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

    // Validate AI settings -- forecastingModel must match the backend
    // ChoiceField at serializers.py:84-87, otherwise the save 400s and the
    // setting silently fails (Finding #16).
    if (
      settings.forecastingModel !== undefined &&
      !isValidForecastingModel(settings.forecastingModel)
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
  // aiApiKey is sent when present; backend masks it on read.
  if (settings.aiApiKey !== undefined) prefs.aiApiKey = settings.aiApiKey;

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
  // AI settings -- guard against legacy or out-of-range values silently
  // poisoning the cache (Finding #16). Only adopt the API value when it
  // matches the current legal set; otherwise leave unset so DEFAULT_SETTINGS
  // applies during the merge.
  if (
    prefs.forecastingModel !== undefined &&
    isValidForecastingModel(prefs.forecastingModel)
  ) {
    settings.forecastingModel = prefs.forecastingModel;
  }
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
        // Best-effort hydration; localStorage already provides the cached
        // settings, so a hydration failure is non-blocking. Surface via
        // console.warn (visible in default devtools) but no toast — the user
        // hasn't taken any action they'd expect feedback for.
        console.warn(
          "Initial settings hydration from backend failed; using localStorage",
          error,
        );
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
      // Save to localStorage immediately (optimistic; primary store)
      const updated = saveSettingsToStorage(settings);

      // Sync to backend if authenticated. Errors propagate so consumers
      // can react via mutation.error / their own onError handlers.
      if (isAuthenticated()) {
        await authAPI.updatePreferences(toApiFormat(settings));
      }

      return updated;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.settings.all, data);
    },
    onError: (error) => {
      // localStorage save already happened optimistically before this fires.
      // Surface the backend-sync failure so the user knows their settings
      // exist locally only.
      toast.error(
        "Settings saved locally but couldn't sync to server. Try again.",
        {
          description:
            error instanceof Error ? error.message : "Unknown error",
        },
      );
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
      // Clear localStorage immediately (optimistic; primary store)
      localStorage.removeItem(SETTINGS_STORAGE_KEY);

      // Sync to backend if authenticated. Errors propagate so consumers
      // can react via mutation.error / their own onError handlers.
      if (isAuthenticated()) {
        await authAPI.replacePreferences({});
      }

      return DEFAULT_SETTINGS;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.settings.all, data);
    },
    onError: (error) => {
      // localStorage clear already happened optimistically before this fires.
      // Surface the backend-sync failure so the user knows their reset is
      // local only.
      toast.error(
        "Settings reset locally but couldn't clear on server. Try again.",
        {
          description:
            error instanceof Error ? error.message : "Unknown error",
        },
      );
    },
  });
}
