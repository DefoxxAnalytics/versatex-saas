/**
 * Tests for Settings Page Component
 *
 * Tests user preference management including:
 * - Loading state display
 * - Profile form inputs and validation
 * - Theme preferences (light/dark mode)
 * - Color scheme preferences (Navy/Classic)
 * - Notification settings
 * - Export format preferences
 * - AI & Predictive Analytics settings
 * - Reset to defaults functionality
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Settings from "../Settings";

// Mock useSettings hooks
vi.mock("@/hooks/useSettings", () => ({
  useSettings: vi.fn(),
  useUpdateSettings: vi.fn(),
  useResetSettings: vi.fn(),
  FORECASTING_MODEL_LABELS: {
    simple_average: "Simple Average",
    linear: "Linear Regression",
    advanced: "Advanced (ML)",
  },
}));

// Mock ThemeContext
vi.mock("@/contexts/ThemeContext", () => ({
  useTheme: vi.fn(() => ({
    theme: "light",
    colorScheme: "navy",
    setTheme: vi.fn(),
    setColorScheme: vi.fn(),
  })),
}));

// Mock AuthContext
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: {
      id: 1,
      username: "testuser",
      profile: { role: "viewer" },
    },
    isAuth: true,
    checkAuth: vi.fn(),
    logout: vi.fn(),
  })),
}));

// Mock useOrganizationSettings hooks (admin savings config section)
vi.mock("@/hooks/useOrganizationSettings", () => ({
  useOrganizationSavingsConfig: vi.fn(() => ({ data: null, isLoading: false })),
  useUpdateOrganizationSavingsConfig: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useExportSavingsConfigPdf: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  getBenchmarkProfileLabel: vi.fn((p: string) => p),
  getBenchmarkProfileDescription: vi.fn(() => ""),
  formatRateAsPercentage: vi.fn((v: number) => `${v}%`),
  formatRateAsCurrency: vi.fn((v: number) => `$${v}`),
  getBenchmarkRangeString: vi.fn(() => ""),
  PROFILE_REALIZATION: {},
}));

// Mock useAIInsights (effectiveness metrics)
vi.mock("@/hooks/useAIInsights", () => ({
  useInsightEffectiveness: vi.fn(() => ({ data: null, isLoading: false })),
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import {
  useSettings,
  useUpdateSettings,
  useResetSettings,
} from "@/hooks/useSettings";
import { useTheme } from "@/contexts/ThemeContext";
import { toast } from "sonner";

// Test wrapper with QueryClient
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

// Default mock settings
const mockSettings = {
  theme: "light" as const,
  colorScheme: "navy" as const,
  notifications: true,
  exportFormat: "csv" as const,
  userName: "Test User",
  userEmail: "test@example.com",
  userRole: "Procurement Manager",
  currency: "USD",
  dateFormat: "MM/DD/YYYY",
  forecastingModel: "simple_average" as const,
  useExternalAI: false,
  aiProvider: "anthropic" as const,
  forecastHorizonMonths: 6,
  anomalySensitivity: 2,
};

describe("Settings Page", () => {
  const mockMutate = vi.fn();
  const mockResetMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    vi.mocked(useSettings).mockReturnValue({
      data: mockSettings,
      isLoading: false,
      error: null,
      isError: false,
      isSuccess: true,
      isPending: false,
      isFetching: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSettings>);

    vi.mocked(useUpdateSettings).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      data: undefined,
      error: null,
      mutateAsync: vi.fn(),
      reset: vi.fn(),
      variables: undefined,
      status: "idle",
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: true,
      isPaused: false,
      submittedAt: 0,
    } as unknown as ReturnType<typeof useUpdateSettings>);

    vi.mocked(useResetSettings).mockReturnValue({
      mutate: mockResetMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      data: undefined,
      error: null,
      mutateAsync: vi.fn(),
      reset: vi.fn(),
      variables: undefined,
      status: "idle",
      context: undefined,
      failureCount: 0,
      failureReason: null,
      isIdle: true,
      isPaused: false,
      submittedAt: 0,
    } as unknown as ReturnType<typeof useResetSettings>);

    vi.mocked(useTheme).mockReturnValue({
      theme: "light",
      colorScheme: "navy",
      setTheme: vi.fn(),
      setColorScheme: vi.fn(),
      switchable: true,
    });
  });

  describe("Loading State", () => {
    it("should display loading state while settings are being fetched", () => {
      vi.mocked(useSettings).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        isPending: true,
        isFetching: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSettings>);

      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Loading settings...")).toBeInTheDocument();
    });
  });

  describe("Page Header", () => {
    it("should display page title and description", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Settings")).toBeInTheDocument();
      expect(
        screen.getByText("Manage your account settings and preferences"),
      ).toBeInTheDocument();
    });
  });

  describe("User Profile Section", () => {
    it("should display user profile card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("User Profile")).toBeInTheDocument();
      expect(
        screen.getByText("Update your personal information"),
      ).toBeInTheDocument();
    });

    it("should populate form fields with current settings", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      await waitFor(() => {
        const nameInput = screen.getByLabelText("Name") as HTMLInputElement;
        const emailInput = screen.getByLabelText("Email") as HTMLInputElement;
        const roleInput = screen.getByLabelText("Role") as HTMLInputElement;

        expect(nameInput.value).toBe("Test User");
        expect(emailInput.value).toBe("test@example.com");
        expect(roleInput.value).toBe("Procurement Manager");
      });
    });

    it("should allow editing profile fields", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      await waitFor(() => {
        const nameInput = screen.getByLabelText("Name") as HTMLInputElement;
        fireEvent.change(nameInput, { target: { value: "New Name" } });
        expect(nameInput.value).toBe("New Name");
      });
    });

    it("should call updateSettings when Save Profile is clicked", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      // Wait for initial values to be set
      await waitFor(() => {
        expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe(
          "Test User",
        );
      });

      // Click save button
      const saveButton = screen.getByText("Save Profile");
      fireEvent.click(saveButton);

      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          userName: "Test User",
          userEmail: "test@example.com",
          userRole: "Procurement Manager",
        }),
        expect.any(Object),
      );
    });

    it("should validate email format", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      await waitFor(() => {
        const emailInput = screen.getByLabelText("Email") as HTMLInputElement;
        fireEvent.change(emailInput, { target: { value: "invalid-email" } });
      });

      const saveButton = screen.getByText("Save Profile");
      fireEvent.click(saveButton);

      expect(toast.error).toHaveBeenCalledWith(
        "Please enter a valid email address",
      );
      expect(mockMutate).not.toHaveBeenCalled();
    });

    it("should allow empty email", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      await waitFor(() => {
        const emailInput = screen.getByLabelText("Email") as HTMLInputElement;
        fireEvent.change(emailInput, { target: { value: "" } });
      });

      const saveButton = screen.getByText("Save Profile");
      fireEvent.click(saveButton);

      // Should not show error for empty email
      expect(toast.error).not.toHaveBeenCalled();
      expect(mockMutate).toHaveBeenCalled();
    });
  });

  describe("Theme Preferences Section", () => {
    it("should display theme preferences card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Theme Preferences")).toBeInTheDocument();
      expect(
        screen.getByText("Customize the look and feel of the application"),
      ).toBeInTheDocument();
    });

    it("should display color scheme selector", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Color Scheme")).toBeInTheDocument();
      expect(
        screen.getByText(/Navy.*Classic.*Versatex Brand/i),
      ).toBeInTheDocument();
    });

    it("should display appearance selector", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Appearance")).toBeInTheDocument();
      expect(
        screen.getByText("Select light or dark mode for the interface"),
      ).toBeInTheDocument();
    });
  });

  describe("Notification Settings Section", () => {
    it("should display notifications card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Notifications")).toBeInTheDocument();
      expect(
        screen.getByText("Manage your notification preferences"),
      ).toBeInTheDocument();
    });

    it("should display notification toggle", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Enable Notifications")).toBeInTheDocument();
      expect(
        screen.getByText("Receive alerts and updates"),
      ).toBeInTheDocument();
    });

    it("should toggle notifications when switch is clicked", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      const notificationSwitch = screen.getByRole("switch", {
        name: /enable notifications/i,
      });
      fireEvent.click(notificationSwitch);

      expect(mockMutate).toHaveBeenCalledWith(
        { notifications: false },
        expect.any(Object),
      );
    });
  });

  describe("Export Preferences Section", () => {
    it("should display export preferences card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Export Preferences")).toBeInTheDocument();
      expect(
        screen.getByText("Set your default export format"),
      ).toBeInTheDocument();
    });

    it("should display export format selector", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Default Export Format")).toBeInTheDocument();
    });
  });

  describe("AI & Predictive Analytics Section", () => {
    it("should display AI settings card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("AI & Predictive Analytics")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Configure AI-powered insights and forecasting settings",
        ),
      ).toBeInTheDocument();
    });

    it("should display forecasting model selector", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Forecasting Model")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Simple Average is the most conservative.*Linear Regression.*Advanced \(ML\)/i,
        ),
      ).toBeInTheDocument();
    });

    it("should display external AI toggle", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(
        screen.getByText("Enable External AI Enhancement"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Use Claude or OpenAI to enhance insights with strategic recommendations",
        ),
      ).toBeInTheDocument();
    });

    it("should display forecast horizon slider", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Forecast Horizon")).toBeInTheDocument();
      expect(screen.getByText("6 months")).toBeInTheDocument();
      expect(
        screen.getByText(
          "How far ahead to forecast spending trends (3-24 months)",
        ),
      ).toBeInTheDocument();
    });

    it("should display anomaly sensitivity slider", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(
        screen.getByText("Anomaly Detection Sensitivity"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Lower values detect more anomalies, higher values only flag extreme outliers",
        ),
      ).toBeInTheDocument();
    });

    it("should not show AI provider options when external AI is disabled", () => {
      vi.mocked(useSettings).mockReturnValue({
        data: { ...mockSettings, useExternalAI: false },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSettings>);

      render(<Settings />, { wrapper: createWrapper() });

      // AI Provider should not be visible
      expect(screen.queryByText("AI Provider")).not.toBeInTheDocument();
    });

    it("should show AI provider options when external AI is enabled", () => {
      vi.mocked(useSettings).mockReturnValue({
        data: { ...mockSettings, useExternalAI: true },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        isPending: false,
        isFetching: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useSettings>);

      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("AI Provider")).toBeInTheDocument();
      expect(screen.getByText("API Key")).toBeInTheDocument();
    });

    it("should toggle external AI", async () => {
      render(<Settings />, { wrapper: createWrapper() });

      const aiSwitch = screen.getByRole("switch", { name: /external ai/i });
      fireEvent.click(aiSwitch);

      expect(mockMutate).toHaveBeenCalledWith(
        { useExternalAI: true },
        expect.any(Object),
      );
    });
  });

  describe("Reset Settings Section", () => {
    it("should display reset settings card", () => {
      render(<Settings />, { wrapper: createWrapper() });

      expect(screen.getByText("Reset Settings")).toBeInTheDocument();
      expect(
        screen.getByText("Reset all settings to their default values"),
      ).toBeInTheDocument();
    });

    it("should have a destructive reset button", () => {
      render(<Settings />, { wrapper: createWrapper() });

      const resetButton = screen.getByRole("button", {
        name: /reset to defaults/i,
      });
      expect(resetButton).toBeInTheDocument();
    });

    it("should show confirmation before reset", () => {
      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<Settings />, { wrapper: createWrapper() });

      const resetButton = screen.getByRole("button", {
        name: /reset to defaults/i,
      });
      fireEvent.click(resetButton);

      expect(confirmSpy).toHaveBeenCalledWith(
        "Are you sure you want to reset all settings to defaults?",
      );
      expect(mockResetMutate).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("should reset settings when confirmed", () => {
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<Settings />, { wrapper: createWrapper() });

      const resetButton = screen.getByRole("button", {
        name: /reset to defaults/i,
      });
      fireEvent.click(resetButton);

      expect(mockResetMutate).toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe("Form Accessibility", () => {
    it("should have proper labels for all form inputs", () => {
      render(<Settings />, { wrapper: createWrapper() });

      // User profile fields - use getByLabelText for inputs with htmlFor
      expect(screen.getByLabelText("Name")).toBeInTheDocument();
      expect(screen.getByLabelText("Email")).toBeInTheDocument();
      expect(screen.getByLabelText("Role")).toBeInTheDocument();

      // Theme settings - Select components
      expect(screen.getByLabelText("Color Scheme")).toBeInTheDocument();
      expect(screen.getByLabelText("Appearance")).toBeInTheDocument();

      // Notifications - verify label text exists
      expect(screen.getByText("Enable Notifications")).toBeInTheDocument();

      // Export format
      expect(
        screen.getByLabelText("Default Export Format"),
      ).toBeInTheDocument();

      // AI settings - verify label text exists for sliders and switches
      expect(screen.getByLabelText("Forecasting Model")).toBeInTheDocument();
      expect(
        screen.getByText("Enable External AI Enhancement"),
      ).toBeInTheDocument();
      expect(screen.getByText("Forecast Horizon")).toBeInTheDocument();
      expect(
        screen.getByText("Anomaly Detection Sensitivity"),
      ).toBeInTheDocument();
    });
  });

  describe("Disabled States", () => {
    it("should disable Save Profile button while mutation is pending", () => {
      vi.mocked(useUpdateSettings).mockReturnValue({
        mutate: mockMutate,
        isPending: true,
        isSuccess: false,
        isError: false,
        data: undefined,
        error: null,
        mutateAsync: vi.fn(),
        reset: vi.fn(),
        variables: undefined,
        status: "pending",
        context: undefined,
        failureCount: 0,
        failureReason: null,
        isIdle: false,
        isPaused: false,
        submittedAt: Date.now(),
      } as unknown as ReturnType<typeof useUpdateSettings>);

      render(<Settings />, { wrapper: createWrapper() });

      const saveButton = screen.getByRole("button", { name: /save profile/i });
      expect(saveButton).toBeDisabled();
    });

    it("should disable Reset button while mutation is pending", () => {
      vi.mocked(useResetSettings).mockReturnValue({
        mutate: mockResetMutate,
        isPending: true,
        isSuccess: false,
        isError: false,
        data: undefined,
        error: null,
        mutateAsync: vi.fn(),
        reset: vi.fn(),
        variables: undefined,
        status: "pending",
        context: undefined,
        failureCount: 0,
        failureReason: null,
        isIdle: false,
        isPaused: false,
        submittedAt: Date.now(),
      } as unknown as ReturnType<typeof useResetSettings>);

      render(<Settings />, { wrapper: createWrapper() });

      const resetButton = screen.getByRole("button", {
        name: /reset to defaults/i,
      });
      expect(resetButton).toBeDisabled();
    });
  });
});
