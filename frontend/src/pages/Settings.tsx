import { useState, useEffect } from "react";
import {
  useSettings,
  useUpdateSettings,
  useResetSettings,
  FORECASTING_MODEL_LABELS,
  type ColorScheme,
  type AIProvider,
  type ForecastingModel,
} from "@/hooks/useSettings";
import {
  useOrganizationSavingsConfig,
  useUpdateOrganizationSavingsConfig,
  useExportSavingsConfigPdf,
  getBenchmarkProfileLabel,
  getBenchmarkProfileDescription,
  formatRateAsPercentage,
  formatRateAsCurrency,
  getBenchmarkRangeString,
  PROFILE_REALIZATION,
} from "@/hooks/useOrganizationSettings";
import { useInsightEffectiveness } from "@/hooks/useAIInsights";
import { useAuth } from "@/contexts/AuthContext";
import { type BenchmarkProfile, type InsightType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { toast } from "sonner";
import {
  User,
  Bell,
  Download,
  Palette,
  RotateCcw,
  Save,
  Sun,
  Moon,
  Brain,
  Sparkles,
  Key,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Info,
  ExternalLink,
  ChevronDown,
  FileDown,
} from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

/**
 * Settings Page Component
 *
 * Features:
 * - User profile management
 * - Theme preferences (light/dark mode)
 * - Color scheme preferences (Navy/Classic)
 * - Notification settings
 * - Export format preferences
 * - Settings persistence
 * - Reset to defaults
 *
 * Security:
 * - Input validation
 * - XSS prevention through React escaping
 * - Sanitized localStorage operations
 *
 * Accessibility:
 * - Proper labels for all inputs
 * - Keyboard navigation
 * - ARIA attributes
 * - Focus management
 */
export default function Settings() {
  const { data: settings, isLoading } = useSettings();
  const updateSettings = useUpdateSettings();
  const resetSettings = useResetSettings();
  const { setTheme, setColorScheme } = useTheme();
  const { user } = useAuth();

  // Organization savings config (admin only)
  const isAdmin = user?.profile?.role === "admin";
  const { data: savingsConfigData, isLoading: savingsConfigLoading } =
    useOrganizationSavingsConfig();
  const updateSavingsConfig = useUpdateOrganizationSavingsConfig();
  const exportPdf = useExportSavingsConfigPdf();
  const { data: effectivenessData } = useInsightEffectiveness();

  // Local state for form inputs - initialized empty, synced via useEffect
  const [userName, setUserName] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [userRole, setUserRole] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);

  // Sync local state when settings load (once)
  useEffect(() => {
    if (settings && !isInitialized) {
      setUserName(settings.userName || "");
      setUserEmail(settings.userEmail || "");
      setUserRole(settings.userRole || "");
      setIsInitialized(true);
    }
  }, [settings, isInitialized]);

  /**
   * Handle profile update
   * Validates and saves user profile information
   */
  const handleProfileUpdate = () => {
    // Basic validation
    if (userEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userEmail)) {
      toast.error("Please enter a valid email address");
      return;
    }

    updateSettings.mutate(
      {
        userName: userName.trim(),
        userEmail: userEmail.trim(),
        userRole: userRole.trim(),
      },
      {
        onSuccess: () => {
          toast.success("Profile updated successfully");
        },
        onError: () => {
          toast.error("Failed to update profile");
        },
      },
    );
  };

  /**
   * Handle theme change (light/dark mode)
   * Updates both settings and applies theme immediately
   */
  const handleThemeChange = (theme: "light" | "dark") => {
    // Apply theme immediately for instant feedback
    if (setTheme) {
      setTheme(theme);
    }

    // Save to settings for persistence
    updateSettings.mutate(
      { theme },
      {
        onSuccess: () => {
          toast.success(`Theme changed to ${theme} mode`);
        },
      },
    );
  };

  /**
   * Handle color scheme change (Navy/Classic)
   * Updates both settings and applies scheme immediately
   */
  const handleColorSchemeChange = (scheme: ColorScheme) => {
    // Apply color scheme immediately for instant feedback
    if (setColorScheme) {
      setColorScheme(scheme);
    }

    // Save to settings for persistence
    updateSettings.mutate(
      { colorScheme: scheme },
      {
        onSuccess: () => {
          const schemeName = scheme === "navy" ? "Navy Blue" : "Classic";
          toast.success(`Color scheme changed to ${schemeName}`);
        },
      },
    );
  };

  /**
   * Handle notification toggle
   */
  const handleNotificationToggle = (enabled: boolean) => {
    updateSettings.mutate(
      { notifications: enabled },
      {
        onSuccess: () => {
          toast.success(`Notifications ${enabled ? "enabled" : "disabled"}`);
        },
      },
    );
  };

  /**
   * Handle export format change
   */
  const handleExportFormatChange = (format: "csv" | "xlsx" | "pdf") => {
    updateSettings.mutate(
      { exportFormat: format },
      {
        onSuccess: () => {
          toast.success(`Default export format set to ${format.toUpperCase()}`);
        },
      },
    );
  };

  /**
   * Handle reset to defaults
   */
  const handleReset = () => {
    if (confirm("Are you sure you want to reset all settings to defaults?")) {
      resetSettings.mutate(undefined, {
        onSuccess: () => {
          setUserName("");
          setUserEmail("");
          setUserRole("");
          // Reset theme context state
          if (setTheme) setTheme("light");
          if (setColorScheme) setColorScheme("navy");
          toast.success("Settings reset to defaults");
        },
        onError: () => {
          toast.error("Failed to reset settings");
        },
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Manage your account settings and preferences
        </p>
      </div>

      <Separator />

      {/* User Profile Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-blue-600" />
            <CardTitle>User Profile</CardTitle>
          </div>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="userName">Name</Label>
            <Input
              id="userName"
              type="text"
              placeholder="Enter your name"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="userEmail">Email</Label>
            <Input
              id="userEmail"
              type="email"
              placeholder="Enter your email"
              value={userEmail}
              onChange={(e) => setUserEmail(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="userRole">Role</Label>
            <Input
              id="userRole"
              type="text"
              placeholder="e.g., Procurement Manager"
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
              maxLength={100}
            />
          </div>

          <Button
            onClick={handleProfileUpdate}
            disabled={updateSettings.isPending}
            className="w-full sm:w-auto"
          >
            <Save className="h-4 w-4 mr-2" />
            Save Profile
          </Button>
        </CardContent>
      </Card>

      {/* Theme Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-purple-600" />
            <CardTitle>Theme Preferences</CardTitle>
          </div>
          <CardDescription>
            Customize the look and feel of the application
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Color Scheme Selection */}
          <div className="space-y-3">
            <Label htmlFor="colorScheme">Color Scheme</Label>
            <Select
              value={settings?.colorScheme || "navy"}
              onValueChange={(value) =>
                handleColorSchemeChange(value as ColorScheme)
              }
            >
              <SelectTrigger id="colorScheme" className="w-full sm:w-[280px]">
                <SelectValue placeholder="Select color scheme" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="navy">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-[#1e3a8a] border border-blue-900" />
                    <span>Navy Blue & White</span>
                  </div>
                </SelectItem>
                <SelectItem value="classic">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-white border border-gray-300" />
                    <span>Classic (Original)</span>
                  </div>
                </SelectItem>
                <SelectItem value="versatex">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-[#FDC00F] border border-[#231F20]" />
                    <span>Versatex Brand</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Navy (modern), Classic (original), or Versatex Brand (signature
              yellow accent on charcoal)
            </p>
          </div>

          <Separator />

          {/* Light/Dark Mode Selection */}
          <div className="space-y-3">
            <Label htmlFor="theme">Appearance</Label>
            <Select
              value={settings?.theme || "light"}
              onValueChange={(value) =>
                handleThemeChange(value as "light" | "dark")
              }
            >
              <SelectTrigger id="theme" className="w-full sm:w-[280px]">
                <SelectValue placeholder="Select appearance" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">
                  <div className="flex items-center gap-2">
                    <Sun className="h-4 w-4" />
                    <span>Light Mode</span>
                  </div>
                </SelectItem>
                <SelectItem value="dark">
                  <div className="flex items-center gap-2">
                    <Moon className="h-4 w-4" />
                    <span>Dark Mode</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Select light or dark mode for the interface
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-yellow-600" />
            <CardTitle>Notifications</CardTitle>
          </div>
          <CardDescription>
            Manage your notification preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="notifications" className="text-base">
                Enable Notifications
              </Label>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Receive alerts and updates
              </p>
            </div>
            <Switch
              id="notifications"
              checked={settings?.notifications || false}
              onCheckedChange={handleNotificationToggle}
            />
          </div>
        </CardContent>
      </Card>

      {/* Export Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Download className="h-5 w-5 text-green-600" />
            <CardTitle>Export Preferences</CardTitle>
          </div>
          <CardDescription>Set your default export format</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="exportFormat">Default Export Format</Label>
            <Select
              value={settings?.exportFormat || "csv"}
              onValueChange={(value) =>
                handleExportFormatChange(value as "csv" | "xlsx" | "pdf")
              }
            >
              <SelectTrigger id="exportFormat" className="w-full sm:w-[200px]">
                <SelectValue placeholder="Select format" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">CSV</SelectItem>
                <SelectItem value="xlsx">Excel (XLSX)</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* AI & Predictive Analytics Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-indigo-600" />
            <CardTitle>AI & Predictive Analytics</CardTitle>
          </div>
          <CardDescription>
            Configure AI-powered insights and forecasting settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Forecasting Model Selection */}
          <div className="space-y-3">
            <Label htmlFor="forecastingModel">Forecasting Model</Label>
            <Select
              value={settings?.forecastingModel ?? "simple_average"}
              onValueChange={(value) => {
                const next = value as ForecastingModel;
                updateSettings.mutate(
                  { forecastingModel: next },
                  {
                    onSuccess: () => {
                      toast.success(
                        `Forecasting model set to ${FORECASTING_MODEL_LABELS[next]}`,
                      );
                    },
                  },
                );
              }}
            >
              <SelectTrigger
                id="forecastingModel"
                className="w-full sm:w-[280px]"
              >
                <SelectValue placeholder="Select forecasting model" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="simple_average">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    <span>{FORECASTING_MODEL_LABELS.simple_average}</span>
                  </div>
                </SelectItem>
                <SelectItem value="linear">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    <span>{FORECASTING_MODEL_LABELS.linear}</span>
                  </div>
                </SelectItem>
                <SelectItem value="advanced">
                  <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    <span>{FORECASTING_MODEL_LABELS.advanced}</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Simple Average is the most conservative; Linear Regression adds
              trend detection; Advanced (ML) layers seasonality and outlier
              handling on top.
            </p>
          </div>

          <Separator />

          {/* External AI Enhancement */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="useExternalAI" className="text-base">
                  Enable External AI Enhancement
                </Label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Use Claude or OpenAI to enhance insights with strategic
                  recommendations
                </p>
              </div>
              <Switch
                id="useExternalAI"
                checked={settings?.useExternalAI || false}
                onCheckedChange={(checked) => {
                  updateSettings.mutate(
                    { useExternalAI: checked },
                    {
                      onSuccess: () => {
                        toast.success(
                          `External AI ${checked ? "enabled" : "disabled"}`,
                        );
                      },
                    },
                  );
                }}
              />
            </div>

            {/* Show AI Provider and API Key only when external AI is enabled */}
            {settings?.useExternalAI && (
              <div className="space-y-4 pl-4 border-l-2 border-indigo-200 dark:border-indigo-800">
                {/* AI Provider Selection */}
                <div className="space-y-2">
                  <Label htmlFor="aiProvider">AI Provider</Label>
                  <Select
                    value={settings?.aiProvider || "anthropic"}
                    onValueChange={(value) => {
                      updateSettings.mutate(
                        { aiProvider: value as AIProvider },
                        {
                          onSuccess: () => {
                            const name =
                              value === "anthropic"
                                ? "Anthropic (Claude)"
                                : "OpenAI (GPT)";
                            toast.success(`AI provider set to ${name}`);
                          },
                        },
                      );
                    }}
                  >
                    <SelectTrigger
                      id="aiProvider"
                      className="w-full sm:w-[280px]"
                    >
                      <SelectValue placeholder="Select AI provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="anthropic">
                        <div className="flex items-center gap-2">
                          <Brain className="h-4 w-4" />
                          <span>Anthropic (Claude)</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="openai">
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4" />
                          <span>OpenAI (GPT)</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* API Key Input */}
                <div className="space-y-2">
                  <Label htmlFor="aiApiKey">API Key</Label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="aiApiKey"
                        type="password"
                        placeholder={
                          settings?.aiApiKey
                            ? "••••••••••••••••"
                            : "Enter your API key"
                        }
                        className="pl-10"
                        maxLength={200}
                        onBlur={(e) => {
                          if (e.target.value) {
                            updateSettings.mutate(
                              { aiApiKey: e.target.value },
                              {
                                onSuccess: () => {
                                  toast.success("API key saved securely");
                                  e.target.value = "";
                                },
                              },
                            );
                          }
                        }}
                      />
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Stored in your user preferences. Treat as sensitive —
                    visible to users with admin access to your account.
                  </p>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Forecast Horizon */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="forecastHorizon">Forecast Horizon</Label>
              <span className="text-sm font-medium">
                {settings?.forecastHorizonMonths || 6} months
              </span>
            </div>
            <Slider
              id="forecastHorizon"
              min={3}
              max={24}
              step={1}
              value={[settings?.forecastHorizonMonths || 6]}
              onValueChange={(value) => {
                updateSettings.mutate(
                  { forecastHorizonMonths: value[0] },
                  {
                    onSuccess: () => {
                      toast.success(
                        `Forecast horizon set to ${value[0]} months`,
                      );
                    },
                  },
                );
              }}
              className="w-full"
            />
            <p className="text-sm text-muted-foreground">
              How far ahead to forecast spending trends (3-24 months)
            </p>
          </div>

          <Separator />

          {/* Anomaly Sensitivity */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="anomalySensitivity">
                Anomaly Detection Sensitivity
              </Label>
              <span className="text-sm font-medium">
                {settings?.anomalySensitivity || 2} (
                {(settings?.anomalySensitivity || 2) <= 2
                  ? "High"
                  : (settings?.anomalySensitivity || 2) <= 3
                    ? "Medium"
                    : "Low"}
                )
              </span>
            </div>
            <Slider
              id="anomalySensitivity"
              min={1}
              max={5}
              step={0.5}
              value={[settings?.anomalySensitivity || 2]}
              onValueChange={(value) => {
                updateSettings.mutate(
                  { anomalySensitivity: value[0] },
                  {
                    onSuccess: () => {
                      const level =
                        value[0] <= 2
                          ? "High"
                          : value[0] <= 3
                            ? "Medium"
                            : "Low";
                      toast.success(`Anomaly sensitivity set to ${level}`);
                    },
                  },
                );
              }}
              className="w-full"
            />
            <p className="text-sm text-muted-foreground">
              Lower values detect more anomalies, higher values only flag
              extreme outliers
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Savings Configuration (Admin Only) */}
      {isAdmin && (
        <Card className="border-green-200 dark:border-green-900">
          <CardHeader>
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-green-600" />
              <CardTitle>Savings Opportunity Rates</CardTitle>
              <Badge variant="outline" className="ml-2 text-xs">
                Admin Only
              </Badge>
            </div>
            <CardDescription>
              Configure industry-benchmark savings rates for AI Insights.
              <br />
              Based on FY2025 Procurement Savings Initiative benchmarks
              (Deloitte, Aberdeen, McKinsey).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {savingsConfigLoading ? (
              <div className="text-sm text-muted-foreground">
                Loading configuration...
              </div>
            ) : (
              <>
                {/* Benchmark Profile Selector */}
                <div className="space-y-3">
                  <Label htmlFor="benchmarkProfile">Benchmark Profile</Label>
                  <Select
                    value={
                      savingsConfigData?.effective_config?.benchmark_profile ||
                      "moderate"
                    }
                    onValueChange={(value: BenchmarkProfile) => {
                      updateSavingsConfig.mutate(
                        { benchmark_profile: value },
                        {
                          onSuccess: () => {
                            toast.success(
                              `Benchmark profile set to ${getBenchmarkProfileLabel(value).split(" ")[0]}`,
                            );
                          },
                          onError: () => {
                            toast.error("Failed to update benchmark profile");
                          },
                        },
                      );
                    }}
                  >
                    <SelectTrigger
                      id="benchmarkProfile"
                      className="w-full sm:w-[400px]"
                    >
                      <SelectValue placeholder="Select benchmark profile" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="conservative">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-blue-500" />
                          <span>
                            Conservative (Risk-averse, 70%+ confidence)
                          </span>
                        </div>
                      </SelectItem>
                      <SelectItem value="moderate">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-green-500" />
                          <span>Moderate (Balanced approach)</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="aggressive">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-orange-500" />
                          <span>Aggressive (Mature procurement)</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="custom">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-purple-500" />
                          <span>Custom (Set your own rates)</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground flex items-start gap-2">
                    <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    {getBenchmarkProfileDescription(
                      savingsConfigData?.effective_config?.benchmark_profile ||
                        "moderate",
                    )}
                  </p>
                  {/* Realization Probability Badge */}
                  {savingsConfigData?.effective_config?.benchmark_profile &&
                    savingsConfigData.effective_config.benchmark_profile !==
                      "custom" && (
                      <div className="flex items-center gap-2 mt-2">
                        <Badge
                          variant={
                            PROFILE_REALIZATION[
                              savingsConfigData.effective_config
                                .benchmark_profile as Exclude<
                                BenchmarkProfile,
                                "custom"
                              >
                            ]?.variant || "secondary"
                          }
                        >
                          {PROFILE_REALIZATION[
                            savingsConfigData.effective_config
                              .benchmark_profile as Exclude<
                              BenchmarkProfile,
                              "custom"
                            >
                          ]?.range || "N/A"}{" "}
                          Achievement
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Historical realization rate for this profile
                        </span>
                      </div>
                    )}
                </div>

                {/* Show current effective rates with ranges */}
                <div className="rounded-lg bg-muted/50 p-4 space-y-3">
                  <h4 className="text-sm font-medium">
                    Current Effective Rates
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Vendor Consolidation:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsPercentage(
                            savingsConfigData?.effective_config
                              ?.consolidation_rate ?? 0.03,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("consolidation_rate")})
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Anomaly Recovery:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsPercentage(
                            savingsConfigData?.effective_config
                              ?.anomaly_recovery_rate ?? 0.008,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("anomaly_recovery_rate")})
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Price Variance Capture:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsPercentage(
                            savingsConfigData?.effective_config
                              ?.price_variance_capture ?? 0.4,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("price_variance_capture")})
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Specification Rate:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsPercentage(
                            savingsConfigData?.effective_config
                              ?.specification_rate ?? 0.03,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("specification_rate")})
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Payment Terms Rate:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsPercentage(
                            savingsConfigData?.effective_config
                              ?.payment_terms_rate ?? 0.008,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("payment_terms_rate")})
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">
                        Process Savings:
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          {formatRateAsCurrency(
                            savingsConfigData?.effective_config
                              ?.process_savings_per_txn ?? 35,
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (range:{" "}
                          {getBenchmarkRangeString("process_savings_per_txn")})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Benchmark Sources (Collapsible) */}
                <Collapsible>
                  <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                    <ChevronDown className="h-4 w-4" />
                    View Benchmark Sources
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pt-3">
                    <div className="rounded-lg bg-blue-50 dark:bg-blue-950/30 p-4 space-y-3 text-sm">
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">
                            Vendor Consolidation (1-8%)
                          </span>
                          <p className="text-muted-foreground">
                            Deloitte Procurement Study, 2024
                          </p>
                        </div>
                        <a
                          href="https://www2.deloitte.com/us/en/pages/operations/articles/procurement-analytics.html"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">
                            Invoice Accuracy (0.5-1.5%)
                          </span>
                          <p className="text-muted-foreground">
                            Aberdeen Group AP Research, 2023
                          </p>
                        </div>
                        <a
                          href="https://www.aberdeen.com/research/accounts-payable"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">
                            Specification Standardization (2-4%)
                          </span>
                          <p className="text-muted-foreground">
                            McKinsey Operations Practice, 2024
                          </p>
                        </div>
                        <a
                          href="https://www.mckinsey.com/capabilities/operations/our-insights"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">
                            Payment Terms Optimization (0.5-1.2%)
                          </span>
                          <p className="text-muted-foreground">
                            Hackett Group Working Capital Study, 2024
                          </p>
                        </div>
                        <a
                          href="https://www.thehackettgroup.com/research/procurement"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <Separator />
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">
                            Process Automation ($25-50/txn)
                          </span>
                          <p className="text-muted-foreground">
                            APQC Process Benchmarking, 2024
                          </p>
                        </div>
                        <a
                          href="https://www.apqc.org/resource-library/resource-listing/procurement-benchmarks"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>

                {/* Historical Performance (if data available) */}
                {effectivenessData &&
                  effectivenessData.savings_metrics?.total_actual_savings >
                    0 && (
                    <div className="rounded-lg bg-amber-50 dark:bg-amber-950/30 p-4 mt-4 border border-amber-200 dark:border-amber-800">
                      <h4 className="text-sm font-medium flex items-center gap-2 mb-3">
                        <TrendingUp className="h-4 w-4 text-amber-600" />
                        Historical Performance
                      </h4>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground block">
                            Projected:
                          </span>
                          <span className="font-medium text-lg">
                            $
                            {effectivenessData.savings_metrics.total_predicted_savings?.toLocaleString() ||
                              "0"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block">
                            Actual:
                          </span>
                          <span className="font-medium text-lg text-green-600 dark:text-green-400">
                            $
                            {effectivenessData.savings_metrics.total_actual_savings?.toLocaleString() ||
                              "0"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground block">
                            Realization:
                          </span>
                          <span className="font-medium text-lg">
                            {effectivenessData.savings_metrics
                              .roi_accuracy_percent != null
                              ? `${effectivenessData.savings_metrics.roi_accuracy_percent.toFixed(0)}%`
                              : "N/A"}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        Based on{" "}
                        {effectivenessData.savings_metrics
                          .implemented_insights || 0}{" "}
                        implemented insights
                      </p>
                    </div>
                  )}

                {/* Custom Rates (shown when profile === 'custom') */}
                {savingsConfigData?.effective_config?.benchmark_profile ===
                  "custom" && (
                  <>
                    <Separator />
                    <div className="space-y-4 pl-4 border-l-2 border-green-200 dark:border-green-800">
                      <h4 className="text-sm font-medium">
                        Custom Rate Configuration
                      </h4>

                      {/* Consolidation Rate */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Vendor Consolidation</Label>
                          <span className="text-sm font-medium">
                            {formatRateAsPercentage(
                              savingsConfigData?.effective_config
                                ?.consolidation_rate ?? 0.03,
                            )}
                          </span>
                        </div>
                        <Slider
                          min={0.5}
                          max={15}
                          step={0.5}
                          value={[
                            (savingsConfigData?.effective_config
                              ?.consolidation_rate ?? 0.03) * 100,
                          ]}
                          onValueCommit={(value) => {
                            updateSavingsConfig.mutate(
                              { consolidation_rate: value[0] / 100 },
                              {
                                onSuccess: () =>
                                  toast.success("Consolidation rate updated"),
                              },
                            );
                          }}
                        />
                        <p className="text-xs text-muted-foreground">
                          Industry benchmark: 1-8% (Deloitte 2024)
                        </p>
                      </div>

                      {/* Anomaly Recovery Rate */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Anomaly/Error Recovery</Label>
                          <span className="text-sm font-medium">
                            {formatRateAsPercentage(
                              savingsConfigData?.effective_config
                                ?.anomaly_recovery_rate ?? 0.008,
                            )}
                          </span>
                        </div>
                        <Slider
                          min={0.1}
                          max={5}
                          step={0.1}
                          value={[
                            (savingsConfigData?.effective_config
                              ?.anomaly_recovery_rate ?? 0.008) * 100,
                          ]}
                          onValueCommit={(value) => {
                            updateSavingsConfig.mutate(
                              { anomaly_recovery_rate: value[0] / 100 },
                              {
                                onSuccess: () =>
                                  toast.success(
                                    "Anomaly recovery rate updated",
                                  ),
                              },
                            );
                          }}
                        />
                        <p className="text-xs text-muted-foreground">
                          Industry benchmark: 0.5-1.5% (Aberdeen Group)
                        </p>
                      </div>

                      {/* Price Variance Capture */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Price Variance Capture</Label>
                          <span className="text-sm font-medium">
                            {formatRateAsPercentage(
                              savingsConfigData?.effective_config
                                ?.price_variance_capture ?? 0.4,
                            )}
                          </span>
                        </div>
                        <Slider
                          min={10}
                          max={90}
                          step={5}
                          value={[
                            (savingsConfigData?.effective_config
                              ?.price_variance_capture ?? 0.4) * 100,
                          ]}
                          onValueCommit={(value) => {
                            updateSavingsConfig.mutate(
                              { price_variance_capture: value[0] / 100 },
                              {
                                onSuccess: () =>
                                  toast.success(
                                    "Price variance capture updated",
                                  ),
                              },
                            );
                          }}
                        />
                        <p className="text-xs text-muted-foreground">
                          Realistic negotiation capture rate (10-90%)
                        </p>
                      </div>
                    </div>
                  </>
                )}

                <Separator />

                {/* Enabled Insights */}
                <div className="space-y-3">
                  <Label>Enabled Insight Types</Label>
                  <div className="grid grid-cols-2 gap-4">
                    {(
                      [
                        { key: "consolidation", label: "Vendor Consolidation" },
                        { key: "anomaly", label: "Anomaly Detection" },
                        {
                          key: "cost_optimization",
                          label: "Cost Optimization",
                        },
                        { key: "risk", label: "Risk Analysis" },
                      ] as const
                    ).map(({ key, label }) => {
                      const enabledInsights = savingsConfigData
                        ?.effective_config?.enabled_insights || [
                        "consolidation",
                        "anomaly",
                        "cost_optimization",
                        "risk",
                      ];
                      const isChecked = enabledInsights.includes(key);
                      return (
                        <div key={key} className="flex items-center space-x-2">
                          <Checkbox
                            id={`insight-${key}`}
                            checked={isChecked}
                            onCheckedChange={(checked) => {
                              const newEnabled = checked
                                ? [...enabledInsights, key]
                                : enabledInsights.filter(
                                    (i: InsightType) => i !== key,
                                  );
                              updateSavingsConfig.mutate(
                                { enabled_insights: newEnabled },
                                {
                                  onSuccess: () =>
                                    toast.success(
                                      `${label} ${checked ? "enabled" : "disabled"}`,
                                    ),
                                },
                              );
                            }}
                          />
                          <label
                            htmlFor={`insight-${key}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            {label}
                          </label>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Disabled insights will not appear in AI Insights analysis
                  </p>
                </div>

                <Separator />

                {/* PDF Export Button */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Export Configuration</Label>
                    <p className="text-sm text-muted-foreground">
                      Download a PDF summary for stakeholder presentations
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      exportPdf.mutate(undefined, {
                        onSuccess: () => {
                          toast.success("Benchmark summary downloaded");
                        },
                        onError: () => {
                          toast.error("Failed to download PDF");
                        },
                      });
                    }}
                    disabled={exportPdf.isPending}
                  >
                    <FileDown className="h-4 w-4 mr-2" />
                    {exportPdf.isPending ? "Downloading..." : "Download PDF"}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Reset Settings */}
      <Card className="border-red-200 dark:border-red-900">
        <CardHeader>
          <div className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5 text-red-600" />
            <CardTitle className="text-red-600">Reset Settings</CardTitle>
          </div>
          <CardDescription>
            Reset all settings to their default values
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            onClick={handleReset}
            disabled={resetSettings.isPending}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset to Defaults
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
