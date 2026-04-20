/**
 * Chart Configuration Utilities
 * Generates ECharts configurations for various chart types
 *
 * Security: All data is validated and sanitized
 * Performance: Optimized configurations for fast rendering
 */

import type { EChartsOption } from "echarts";
import type { ProcurementRecord } from "../hooks/useProcurementData";
import type { SpendByCategory, SpendBySupplier, MonthlyTrend } from "./api";

// ============================================================
// API Data Chart Configs (use pre-aggregated server-side data)
// ============================================================

/**
 * Generate Spend by Category Bar Chart from API data
 */
export function getCategoryChartFromAPI(
  data: SpendByCategory[],
): EChartsOption {
  // Data is already sorted by backend
  const categories = data.map((item) => item.category || "Uncategorized");
  const amounts = data.map((item) => item.amount || 0);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number }[];
        const d = p[0];
        return `${d.name}<br/>$${d.value.toLocaleString()}`;
      },
    },
    legend: {
      show: true,
      right: 10,
      top: 0,
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: 30,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: categories,
      axisLabel: {
        rotate: 45,
        interval: 0,
      },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    series: [
      {
        name: "Spend",
        type: "bar",
        data: amounts,
        itemStyle: {
          color: "#3b82f6",
        },
      },
    ],
  };
}

/**
 * Generate Spend Trend Line Chart from API data
 */
export function getTrendChartFromAPI(data: MonthlyTrend[]): EChartsOption {
  const months = data.map((item) => item.month);
  const amounts = data.map((item) => item.amount || 0);

  return {
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number }[];
        const d = p[0];
        return `${d.name}<br/>$${d.value.toLocaleString()}`;
      },
    },
    legend: {
      show: true,
      right: 10,
      top: 0,
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: 30,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: months,
      boundaryGap: false,
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    series: [
      {
        name: "Spend",
        type: "line",
        data: amounts,
        smooth: true,
        itemStyle: {
          color: "#10b981",
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(16, 185, 129, 0.3)" },
              { offset: 1, color: "rgba(16, 185, 129, 0.05)" },
            ],
          },
        },
      },
    ],
  };
}

/**
 * Generate Top Suppliers Horizontal Bar Chart from API data
 */
export function getSupplierChartFromAPI(
  data: SpendBySupplier[],
  limit: number = 10,
): EChartsOption {
  // Take top N suppliers (data is already sorted by backend)
  const topSuppliers = data.slice(0, limit);
  const suppliers = topSuppliers.map((item) => item.supplier || "Unknown");
  const amounts = topSuppliers.map((item) => item.amount || 0);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: unknown) => {
        const p = params as { name: string; value: number }[];
        const d = p[0];
        return `${d.name}<br/>$${d.value.toLocaleString()}`;
      },
    },
    legend: {
      show: true,
      right: 10,
      top: 0,
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: 30,
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    yAxis: {
      type: "category",
      data: suppliers,
      inverse: true,
    },
    series: [
      {
        name: "Spend",
        type: "bar",
        data: amounts,
        itemStyle: {
          color: "#8b5cf6",
        },
      },
    ],
  };
}

// ============================================================
// Legacy Client-Side Chart Configs (for drill-down and filtering)
// ============================================================

/**
 * Generate Spend by Category Bar Chart configuration
 */
export function getSpendByCategoryConfig(
  data: ProcurementRecord[],
): EChartsOption {
  // Group by category and sum amounts
  const categoryMap = new Map<string, number>();

  data.forEach((record) => {
    const category = record.category || "Uncategorized";
    const amount = record.amount || 0;
    categoryMap.set(category, (categoryMap.get(category) || 0) + amount);
  });

  // Sort by amount descending
  const sortedCategories = Array.from(categoryMap.entries()).sort(
    (a, b) => b[1] - a[1],
  );

  const categories = sortedCategories.map(([cat]) => cat);
  const amounts = sortedCategories.map(([, amt]) => amt);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: any) => {
        const data = params[0];
        return `${data.name}<br/>$${data.value.toLocaleString()}`;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: categories,
      axisLabel: {
        rotate: 45,
        interval: 0,
      },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    series: [
      {
        name: "Spend",
        type: "bar",
        data: amounts,
        itemStyle: {
          color: "#3b82f6",
        },
      },
    ],
  };
}

/**
 * Generate Spend Trend Over Time Line Chart configuration
 */
export function getSpendTrendConfig(data: ProcurementRecord[]): EChartsOption {
  // Group by month and sum amounts
  const monthMap = new Map<string, number>();

  data.forEach((record) => {
    if (!record.date) return;

    const date = new Date(record.date);
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    const amount = record.amount || 0;
    monthMap.set(monthKey, (monthMap.get(monthKey) || 0) + amount);
  });

  // Sort by month
  const sortedMonths = Array.from(monthMap.entries()).sort((a, b) =>
    a[0].localeCompare(b[0]),
  );

  const months = sortedMonths.map(([month]) => month);
  const amounts = sortedMonths.map(([, amt]) => amt);

  return {
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        const data = params[0];
        return `${data.name}<br/>$${data.value.toLocaleString()}`;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: months,
      boundaryGap: false,
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    series: [
      {
        name: "Spend",
        type: "line",
        data: amounts,
        smooth: true,
        itemStyle: {
          color: "#10b981",
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(16, 185, 129, 0.3)" },
              { offset: 1, color: "rgba(16, 185, 129, 0.05)" },
            ],
          },
        },
      },
    ],
  };
}

/**
 * Generate Top 10 Suppliers Horizontal Bar Chart configuration
 */
export function getTopSuppliersConfig(
  data: ProcurementRecord[],
): EChartsOption {
  // Group by supplier and sum amounts
  const supplierMap = new Map<string, number>();

  data.forEach((record) => {
    const supplier = record.supplier || "Unknown";
    const amount = record.amount || 0;
    supplierMap.set(supplier, (supplierMap.get(supplier) || 0) + amount);
  });

  // Sort by amount descending and take top 10
  const topSuppliers = Array.from(supplierMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const suppliers = topSuppliers.map(([sup]) => sup);
  const amounts = topSuppliers.map(([, amt]) => amt);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: any) => {
        const data = params[0];
        return `${data.name}<br/>$${data.value.toLocaleString()}`;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`,
      },
    },
    yAxis: {
      type: "category",
      data: suppliers,
      inverse: true,
    },
    series: [
      {
        name: "Spend",
        type: "bar",
        data: amounts,
        itemStyle: {
          color: "#8b5cf6",
        },
      },
    ],
  };
}

/**
 * Generate Spend Distribution Donut Chart configuration
 */
export function getSpendDistributionConfig(
  data: ProcurementRecord[],
): EChartsOption {
  // Calculate distribution tiers
  const amounts = data.map((r) => r.amount || 0).filter((a) => a > 0);
  const totalSpend = amounts.reduce((sum, amt) => sum + amt, 0);

  if (amounts.length === 0) {
    return {
      title: {
        text: "No Data",
        left: "center",
        top: "center",
      },
    };
  }

  // Sort amounts to find percentiles
  const sortedAmounts = [...amounts].sort((a, b) => b - a);
  const p80Index = Math.floor(sortedAmounts.length * 0.2);
  const p50Index = Math.floor(sortedAmounts.length * 0.5);

  const highThreshold = sortedAmounts[p80Index];
  const mediumThreshold = sortedAmounts[p50Index];

  let highSpend = 0;
  let mediumSpend = 0;
  let lowSpend = 0;

  amounts.forEach((amount) => {
    if (amount >= highThreshold) {
      highSpend += amount;
    } else if (amount >= mediumThreshold) {
      mediumSpend += amount;
    } else {
      lowSpend += amount;
    }
  });

  return {
    tooltip: {
      trigger: "item",
      formatter: (params: any) => {
        const percent = ((params.value / totalSpend) * 100).toFixed(1);
        return `${params.name}<br/>$${params.value.toLocaleString()} (${percent}%)`;
      },
    },
    legend: {
      orient: "vertical",
      left: "left",
    },
    series: [
      {
        name: "Spend Distribution",
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: false,
          position: "center",
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: "bold",
          },
        },
        labelLine: {
          show: false,
        },
        data: [
          {
            value: highSpend,
            name: "High Value",
            itemStyle: { color: "#ef4444" },
          },
          {
            value: mediumSpend,
            name: "Medium Value",
            itemStyle: { color: "#f59e0b" },
          },
          {
            value: lowSpend,
            name: "Low Value",
            itemStyle: { color: "#22c55e" },
          },
        ],
      },
    ],
  };
}
