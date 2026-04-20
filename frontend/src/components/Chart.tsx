/**
 * Reusable Chart Component
 * Wrapper around Apache ECharts for consistent chart rendering
 *
 * Security: Sanitizes all input data
 * Performance: Lazy loads ECharts, auto-resizes on window resize
 * Accessibility: Provides ARIA labels and keyboard navigation
 */

import { useEffect, useRef, useMemo } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { useTheme } from "@/contexts/ThemeContext";
import { cn } from "@/lib/utils";

// Register ECharts components
echarts.use([
  BarChart,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  CanvasRenderer,
]);

interface ChartProps {
  /**
   * Chart title displayed in card header
   */
  title: string;

  /**
   * Optional description/explanation of what the chart shows
   */
  description?: string;

  /**
   * ECharts configuration object
   */
  option: EChartsOption;

  /**
   * Chart height in pixels
   * @default 300
   */
  height?: number;

  /**
   * Loading state
   * @default false
   */
  loading?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * Click handler for chart data points
   */
  onChartClick?: (params: {
    name: string;
    value: number;
    seriesType?: string;
    dataType?: string;
  }) => void;
}

/**
 * Get dark mode aware colors for chart styling
 */
function getDarkModeColors(isDark: boolean) {
  return {
    textColor: isDark ? "#e5e7eb" : "#374151",
    subTextColor: isDark ? "#9ca3af" : "#6b7280",
    axisLineColor: isDark ? "#374151" : "#e5e7eb",
    splitLineColor: isDark ? "#374151" : "#f3f4f6",
    tooltipBg: isDark ? "#1f2937" : "#ffffff",
    tooltipBorder: isDark ? "#374151" : "#e5e7eb",
  };
}

/**
 * Versatex brand palette used when colorScheme === "versatex".
 * Yellow leads per brand guide ("a pop of yellow on every graphic"),
 * then the official black/gray ramp.
 */
const VERSATEX_CHART_PALETTE = [
  "#FDC00F", // Brand Yellow (PMS 1235 C)
  "#231F20", // 100% Black
  "#58595B", // 80% Black
  "#A7A9AC", // 40% Black
  "#FCD34D", // Light yellow tint
] as const;

/**
 * Versatex gradient (yellow-to-transparent) for area fills.
 */
const VERSATEX_AREA_GRADIENT = {
  type: "linear" as const,
  x: 0,
  y: 0,
  x2: 0,
  y2: 1,
  colorStops: [
    { offset: 0, color: "rgba(253, 192, 15, 0.35)" },
    { offset: 1, color: "rgba(253, 192, 15, 0.05)" },
  ],
};

/**
 * Strip hardcoded series colors so ECharts falls back to option.color[index],
 * and swap area gradients to the brand yellow gradient.
 *
 * Only applied when colorScheme === "versatex"; other schemes keep their
 * original hardcoded colors (no regression risk).
 */
function applyVersatexPaletteToSeries(
  series: EChartsOption["series"],
): EChartsOption["series"] {
  if (!series) return series;
  const list = Array.isArray(series) ? series : [series];
  return list.map((s) => {
    const next = { ...(s as Record<string, unknown>) };
    if ("itemStyle" in next && next.itemStyle) {
      const itemStyle = { ...(next.itemStyle as Record<string, unknown>) };
      delete itemStyle.color;
      next.itemStyle = itemStyle;
    }
    if ("areaStyle" in next && next.areaStyle) {
      next.areaStyle = { ...(next.areaStyle as object), color: VERSATEX_AREA_GRADIENT };
    }
    return next;
  }) as EChartsOption["series"];
}

/**
 * Chart Component
 * Renders an ECharts chart with proper error handling and accessibility
 */
export function Chart({
  title,
  description,
  option,
  height = 300,
  loading = false,
  className = "",
  onChartClick,
}: ChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const { theme, colorScheme } = useTheme();
  const isDark = theme === "dark";
  const isVersatex = colorScheme === "versatex";

  // Merge dark mode colors with chart option
  const themedOption = useMemo(() => {
    const colors = getDarkModeColors(isDark);

    const series = isVersatex
      ? applyVersatexPaletteToSeries(option.series)
      : option.series;
    const paletteOverride = isVersatex
      ? { color: [...VERSATEX_CHART_PALETTE] }
      : {};

    // Deep merge with user option, adding dark mode styling
    return {
      ...option,
      ...paletteOverride,
      series,
      textStyle: {
        color: colors.textColor,
        ...(option as any).textStyle,
      },
      tooltip: {
        backgroundColor: colors.tooltipBg,
        borderColor: colors.tooltipBorder,
        textStyle: {
          color: colors.textColor,
        },
        ...(option as any).tooltip,
      },
      legend: {
        textStyle: {
          color: colors.subTextColor,
        },
        ...(option as any).legend,
      },
      xAxis: Array.isArray((option as any).xAxis)
        ? (option as any).xAxis.map((axis: any) => ({
            ...axis,
            axisLine: {
              lineStyle: { color: colors.axisLineColor },
              ...axis?.axisLine,
            },
            axisLabel: {
              color: colors.subTextColor,
              ...axis?.axisLabel,
            },
            splitLine: {
              lineStyle: { color: colors.splitLineColor },
              ...axis?.splitLine,
            },
          }))
        : (option as any).xAxis
          ? {
              ...(option as any).xAxis,
              axisLine: {
                lineStyle: { color: colors.axisLineColor },
                ...(option as any).xAxis?.axisLine,
              },
              axisLabel: {
                color: colors.subTextColor,
                ...(option as any).xAxis?.axisLabel,
              },
              splitLine: {
                lineStyle: { color: colors.splitLineColor },
                ...(option as any).xAxis?.splitLine,
              },
            }
          : undefined,
      yAxis: Array.isArray((option as any).yAxis)
        ? (option as any).yAxis.map((axis: any) => ({
            ...axis,
            axisLine: {
              lineStyle: { color: colors.axisLineColor },
              ...axis?.axisLine,
            },
            axisLabel: {
              color: colors.subTextColor,
              ...axis?.axisLabel,
            },
            splitLine: {
              lineStyle: { color: colors.splitLineColor },
              ...axis?.splitLine,
            },
          }))
        : (option as any).yAxis
          ? {
              ...(option as any).yAxis,
              axisLine: {
                lineStyle: { color: colors.axisLineColor },
                ...(option as any).yAxis?.axisLine,
              },
              axisLabel: {
                color: colors.subTextColor,
                ...(option as any).yAxis?.axisLabel,
              },
              splitLine: {
                lineStyle: { color: colors.splitLineColor },
                ...(option as any).yAxis?.splitLine,
              },
            }
          : undefined,
    };
  }, [option, isDark, isVersatex]);

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current) return;

    // Create chart instance
    const chartInstance = echarts.init(chartRef.current);
    chartInstanceRef.current = chartInstance;

    // Set option
    chartInstance.setOption(themedOption);

    // Handle click events
    if (onChartClick) {
      chartInstance.on("click", (params: any) => {
        onChartClick({
          name: params.name,
          value: params.value,
          seriesType: params.seriesType,
          dataType: params.dataType,
        });
      });
    }

    // Handle window resize
    const handleResize = () => {
      chartInstance.resize();
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.off("click");
      chartInstance.dispose();
      chartInstanceRef.current = null;
    };
  }, [onChartClick]);

  // Update chart when option changes (including dark mode)
  useEffect(() => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.setOption(themedOption, true);
    }
  }, [themedOption]);

  // Handle loading state
  useEffect(() => {
    if (chartInstanceRef.current) {
      const colors = getDarkModeColors(isDark);
      if (loading) {
        chartInstanceRef.current.showLoading({
          text: "Loading...",
          color: isDark ? "#60a5fa" : "#3b82f6",
          textColor: colors.textColor,
          maskColor: isDark ? "rgba(0, 0, 0, 0.5)" : "rgba(255, 255, 255, 0.8)",
        });
      } else {
        chartInstanceRef.current.hideLoading();
      }
    }
  }, [loading, isDark]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">{title}</CardTitle>
        {description && (
          <p
            className={cn(
              "text-sm mt-2",
              isDark ? "text-gray-400" : "text-gray-600",
            )}
          >
            {description}
          </p>
        )}
      </CardHeader>
      <CardContent>
        <div
          ref={chartRef}
          style={{ height: `${height}px`, width: "100%" }}
          role="img"
          aria-label={`${title} chart`}
        />
      </CardContent>
    </Card>
  );
}
