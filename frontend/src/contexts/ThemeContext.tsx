import React, { createContext, useContext, useEffect, useState } from "react";
import { useSettings, type ColorScheme } from "@/hooks/useSettings";

type Theme = "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  colorScheme: ColorScheme;
  toggleTheme?: () => void;
  setTheme?: (theme: Theme) => void;
  setColorScheme?: (scheme: ColorScheme) => void;
  switchable: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  defaultColorScheme?: ColorScheme;
  switchable?: boolean;
}

/**
 * Theme Provider Component
 *
 * Features:
 * - Syncs with user settings from useSettings hook (single source of truth)
 * - Applies theme (light/dark) to document root
 * - Applies color scheme (navy/classic) to document root
 * - Supports both theme and color scheme switching
 * - Smooth transitions between themes
 *
 * CSS Classes Applied:
 * - .dark - for dark mode
 * - .classic - for classic color scheme (navy is default, no class)
 * - .versatex - for Versatex brand color scheme (grayscale + yellow accent)
 *
 * Settings persistence is handled by useSettings hook (localStorage).
 * This context only manages the UI state and DOM class application.
 */
export function ThemeProvider({
  children,
  defaultTheme = "light",
  defaultColorScheme = "navy",
  switchable = true,
}: ThemeProviderProps) {
  const { data: settings } = useSettings();

  // Initialize theme from defaults - will sync from settings when loaded
  const [theme, setThemeState] = useState<Theme>(defaultTheme);
  const [colorScheme, setColorSchemeState] =
    useState<ColorScheme>(defaultColorScheme);

  // Sync theme and color scheme with settings when they load
  useEffect(() => {
    if (settings) {
      if (settings.theme && settings.theme !== theme) {
        setThemeState(settings.theme);
      }
      if (settings.colorScheme && settings.colorScheme !== colorScheme) {
        setColorSchemeState(settings.colorScheme);
      }
    }
    // Intentionally only depend on settings to avoid loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings]);

  // Apply theme and color scheme CSS classes to document root
  useEffect(() => {
    const root = document.documentElement;

    // Apply light/dark theme
    root.classList.toggle("dark", theme === "dark");

    // Apply color scheme (navy is default with no class; classic and versatex each add a class)
    root.classList.toggle("classic", colorScheme === "classic");
    root.classList.toggle("versatex", colorScheme === "versatex");
  }, [theme, colorScheme]);

  /**
   * Toggle between light and dark themes
   */
  const toggleTheme = switchable
    ? () => {
        setThemeState((prev) => (prev === "light" ? "dark" : "light"));
      }
    : undefined;

  /**
   * Set theme directly
   * Used by Settings page to apply theme changes immediately
   */
  const setTheme = switchable
    ? (newTheme: Theme) => {
        setThemeState(newTheme);
      }
    : undefined;

  /**
   * Set color scheme directly
   * Used by Settings page to apply color scheme changes immediately
   */
  const setColorScheme = switchable
    ? (newScheme: ColorScheme) => {
        setColorSchemeState(newScheme);
      }
    : undefined;

  return (
    <ThemeContext.Provider
      value={{
        theme,
        colorScheme,
        toggleTheme,
        setTheme,
        setColorScheme,
        switchable,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context
 *
 * @throws Error if used outside ThemeProvider
 *
 * @example
 * ```tsx
 * const { theme, colorScheme, setTheme, setColorScheme } = useTheme();
 *
 * // Toggle theme
 * toggleTheme();
 *
 * // Set specific theme
 * setTheme('dark');
 *
 * // Set color scheme
 * setColorScheme('classic');
 * ```
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
