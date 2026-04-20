import { useState, useMemo } from "react";
import {
  useDetailedSeasonality,
  useSeasonalityCategoryDrilldown,
} from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sun,
  TrendingUp,
  TrendingDown,
  Target,
  Lightbulb,
  Calendar,
  X,
  Users,
  DollarSign,
  BarChart3,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import type { CategorySeasonality } from "@/lib/api";

// Line colors for chart
const LINE_COLORS = ["#06b6d4", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"];

// Heatmap color function
function getHeatmapColor(index: number): string {
  // index ~100 is average
  if (index < 70) return "bg-blue-500 text-white";
  if (index < 85)
    return "bg-blue-300 text-blue-900 dark:bg-blue-700 dark:text-blue-100";
  if (index < 95)
    return "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200";
  if (index <= 105)
    return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
  if (index <= 115)
    return "bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-200";
  if (index <= 130)
    return "bg-orange-300 text-orange-900 dark:bg-orange-700 dark:text-orange-100";
  return "bg-red-500 text-white";
}

// Seasonal Index Heatmap Component
function SeasonalityHeatmap({
  categories,
  monthNames,
  onCategoryClick,
}: {
  categories: CategorySeasonality[];
  monthNames: string[];
  onCategoryClick?: (categoryId: number | null) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          Seasonal Index Heatmap
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Click any row to see supplier details for that category. Values show
          seasonal index (100 = average).
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b dark:border-gray-700">
                <th className="text-left p-2 sticky left-0 bg-white dark:bg-gray-900 font-semibold min-w-[150px]">
                  Category
                </th>
                {monthNames.map((month) => (
                  <th
                    key={month}
                    className="p-2 text-center font-semibold min-w-[50px]"
                  >
                    {month}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr
                  key={cat.category_id}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 border-b dark:border-gray-700 transition-colors"
                  onClick={() => onCategoryClick?.(cat.category_id)}
                >
                  <td
                    className="p-2 font-medium sticky left-0 bg-white dark:bg-gray-900 truncate max-w-[150px]"
                    title={cat.category}
                  >
                    {cat.category}
                  </td>
                  {cat.seasonal_indices.map((index, idx) => (
                    <td
                      key={idx}
                      className={`p-2 text-center font-medium ${getHeatmapColor(index)} transition-colors`}
                      title={`${monthNames[idx]}: ${index.toFixed(0)} (${index > 100 ? "above" : index < 100 ? "below" : "at"} average)`}
                    >
                      {index.toFixed(0)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Legend */}
        <div className="flex items-center justify-center gap-4 mt-4 text-xs flex-wrap">
          <span className="flex items-center gap-1">
            <div className="w-4 h-4 bg-blue-500 rounded" /> Low (&lt;70)
          </span>
          <span className="flex items-center gap-1">
            <div className="w-4 h-4 bg-blue-100 dark:bg-blue-900/50 border rounded" />{" "}
            Below Avg
          </span>
          <span className="flex items-center gap-1">
            <div className="w-4 h-4 bg-gray-100 dark:bg-gray-700 border rounded" />{" "}
            Average (100)
          </span>
          <span className="flex items-center gap-1">
            <div className="w-4 h-4 bg-orange-100 dark:bg-orange-900/50 border rounded" />{" "}
            Above Avg
          </span>
          <span className="flex items-center gap-1">
            <div className="w-4 h-4 bg-red-500 rounded" /> High (&gt;130)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Seasonality() {
  const [useFiscalYear, setUseFiscalYear] = useState(true);
  const [viewMode, setViewMode] = useState<"all" | number>("all");
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null,
  );

  // Fetch data from backend with fiscal year preference
  const { data, isLoading, error } = useDetailedSeasonality(useFiscalYear);

  // Fetch category drilldown when a category is selected
  const { data: drilldownData, isLoading: drilldownLoading } =
    useSeasonalityCategoryDrilldown(selectedCategoryId, useFiscalYear);

  // Extract data from response
  const summary = data?.summary;
  const monthlyData = data?.monthly_data ?? [];
  const categorySeasonality = data?.category_seasonality ?? [];
  const availableYears = summary?.available_years ?? [];

  // Month names based on fiscal year setting
  const monthNames = useMemo(() => {
    if (useFiscalYear) {
      return [
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
      ];
    }
    return [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
  }, [useFiscalYear]);

  // Transform monthly data for chart
  const monthlyChartData = useMemo(() => {
    return monthlyData.map((month) => {
      const chartPoint: Record<string, number | string> = {
        month: month.month,
        fiscalMonth: month.fiscal_month,
        Average: month.average,
      };
      // Add each year's data
      Object.entries(month.years).forEach(([yearKey, value]) => {
        chartPoint[yearKey] = value;
      });
      return chartPoint;
    });
  }, [monthlyData]);

  // Get recent fiscal years for YoY display
  const recentYears = useMemo(() => {
    if (availableYears.length >= 2) {
      const sorted = [...availableYears].sort((a, b) => a - b);
      return sorted.slice(-2);
    }
    return availableYears;
  }, [availableYears]);

  // Handle category card click
  const handleCategoryClick = (categoryId: number | null) => {
    setSelectedCategoryId(categoryId);
  };

  // Loading state with skeleton
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Card className="bg-gradient-to-r from-cyan-50 to-blue-50 border-2 border-cyan-200">
          <CardContent className="pt-6">
            <div className="text-center mb-6">
              <Skeleton className="h-8 w-96 mx-auto" />
            </div>
            <div className="grid grid-cols-4 gap-4 mb-6">
              {[1, 2, 3, 4].map((i) => (
                <Card key={i} className="bg-white">
                  <CardContent className="pt-6 text-center">
                    <Skeleton className="h-10 w-24 mx-auto mb-2" />
                    <Skeleton className="h-4 w-32 mx-auto" />
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[400px] w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-8">
        <Calendar className="h-16 w-16 text-red-400 mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          Error Loading Data
        </h3>
        <p className="text-gray-600 mb-4">
          Failed to load seasonality analysis. Please try again.
        </p>
        <p className="text-sm text-red-500">{errorMessage}</p>
      </div>
    );
  }

  // Empty state
  if (!data || categorySeasonality.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-8">
        <Calendar className="h-16 w-16 text-gray-400 mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          Seasonality Analysis Ready
        </h3>
        <p className="text-gray-600 mb-4">
          Upload your procurement data with date information to discover
          seasonal patterns and optimization opportunities.
        </p>
        <p className="text-sm text-gray-500">
          <strong>Required columns:</strong> Date, Amount, Category, Supplier
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header Card */}
      <Card className="bg-gradient-to-r from-cyan-50 to-blue-50 border-2 border-cyan-200 dark:from-cyan-950/30 dark:to-blue-950/30 dark:border-cyan-800">
        <CardContent className="pt-6">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 flex items-center justify-center gap-2">
              <Sun className="h-6 w-6 text-yellow-500" />
              Seasonality Intelligence & Optimization Opportunities
            </h1>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <Card className="bg-white dark:bg-gray-800">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                  {summary?.categories_analyzed ?? 0}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Categories Analyzed
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white dark:bg-gray-800">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                  {summary?.opportunities_found ?? 0}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Opportunities Found
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white dark:bg-gray-800">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                  {summary?.high_impact_count ?? 0}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  High Impact
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white dark:bg-gray-800">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-cyan-600 dark:text-cyan-400">
                  $
                  {(summary?.total_savings_potential ?? 0).toLocaleString(
                    undefined,
                    { minimumFractionDigits: 0, maximumFractionDigits: 0 },
                  )}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Savings Potential
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Key Insights */}
          <Card className="bg-white dark:bg-gray-800">
            <CardContent className="pt-4">
              <div className="flex items-start gap-2">
                <Target className="h-5 w-5 text-pink-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-gray-800 dark:text-gray-200">
                    Key Insights
                  </span>
                  <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                    Analysis of {summary?.categories_analyzed ?? 0} categories
                    revealed {summary?.opportunities_found ?? 0} optimization
                    opportunities with potential savings of $
                    {(summary?.total_savings_potential ?? 0).toLocaleString()}.{" "}
                    {summary?.high_impact_count ?? 0} high-impact opportunities
                    identified for immediate action.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>

      {/* View Controls */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            View Mode:
          </span>
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={viewMode === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("all")}
            >
              All Years
            </Button>
            {availableYears.map((year) => (
              <Button
                key={year}
                variant={viewMode === year ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode(year)}
              >
                FY{year}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium">Years Available:</span>{" "}
            {availableYears.map((y) => `FY${y}`).join(", ")}
            {availableYears.length >= 2 && (
              <>
                {" | "}
                <span className="font-medium">Avg YoY Growth %:</span>{" "}
                <span
                  className={
                    (summary?.avg_yoy_growth ?? 0) >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }
                >
                  {(summary?.avg_yoy_growth ?? 0) >= 0 ? "+" : ""}
                  {(summary?.avg_yoy_growth ?? 0).toFixed(1)}%
                </span>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="fiscal-year"
              checked={useFiscalYear}
              onCheckedChange={(checked) =>
                setUseFiscalYear(checked as boolean)
              }
            />
            <label
              htmlFor="fiscal-year"
              className="text-sm font-medium text-blue-600 dark:text-blue-400 cursor-pointer"
            >
              Use Fiscal Year (Jul-Jun)
            </label>
          </div>
        </div>
      </div>

      {/* Seasonality Summary */}
      {categorySeasonality.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {/* Highest Seasonality */}
          <Card className="border-l-4 border-l-orange-500">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Highest Seasonality
                  </h3>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {categorySeasonality[0].category}
                  </p>
                  <div className="mt-2 space-y-1">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Strength:</span>{" "}
                      {categorySeasonality[0].seasonality_strength.toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Peak:</span>{" "}
                      {categorySeasonality[0].peak_month} |
                      <span className="font-medium"> Low:</span>{" "}
                      {categorySeasonality[0].low_month}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Lowest Seasonality */}
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <TrendingDown className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Lowest Seasonality
                  </h3>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {
                      categorySeasonality[categorySeasonality.length - 1]
                        .category
                    }
                  </p>
                  <div className="mt-2 space-y-1">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Strength:</span>{" "}
                      {categorySeasonality[
                        categorySeasonality.length - 1
                      ].seasonality_strength.toFixed(1)}
                      %
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Peak:</span>{" "}
                      {
                        categorySeasonality[categorySeasonality.length - 1]
                          .peak_month
                      }{" "}
                      |<span className="font-medium"> Low:</span>{" "}
                      {
                        categorySeasonality[categorySeasonality.length - 1]
                          .low_month
                      }
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Seasonal Patterns Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Seasonal Patterns Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center mb-4">
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
              {viewMode === "all"
                ? `Multi-Year Seasonality Analysis (${useFiscalYear ? "Fiscal Year" : "Calendar Year"})`
                : `FY${viewMode} Seasonality Analysis (${useFiscalYear ? "Fiscal Year" : "Calendar Year"})`}
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={monthlyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="month"
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
                label={{
                  value: useFiscalYear ? "Fiscal Year Month" : "Calendar Month",
                  position: "insideBottom",
                  offset: -5,
                }}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
                tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
                label={{
                  value: "Total Spend",
                  angle: -90,
                  position: "insideLeft",
                }}
              />
              <Tooltip
                formatter={(value: number) =>
                  `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
                }
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
              />
              <Legend verticalAlign="top" height={36} iconType="circle" />
              {viewMode === "all" ? (
                // Show all years plus average when in "All Years" mode
                <>
                  {availableYears.map((year, idx) => (
                    <Line
                      key={year}
                      type="monotone"
                      dataKey={`FY${year}`}
                      stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                  <Line
                    type="monotone"
                    dataKey="Average"
                    stroke="#6b7280"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 3 }}
                  />
                </>
              ) : (
                // Show only selected year when specific year is selected
                <Line
                  type="monotone"
                  dataKey={`FY${viewMode}`}
                  stroke="#06b6d4"
                  strokeWidth={3}
                  dot={{ r: 5 }}
                  activeDot={{ r: 7 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Seasonal Index Heatmap */}
      <SeasonalityHeatmap
        categories={categorySeasonality}
        monthNames={monthNames}
        onCategoryClick={handleCategoryClick}
      />

      {/* Category Opportunity Cards */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">
          Category Opportunities
          <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
            (Click any card for supplier details)
          </span>
        </h2>
        {categorySeasonality.map((category, idx) => {
          // Get FY totals for display
          const fyKeys = Object.keys(category.fy_totals).sort();
          const prevFY = fyKeys.length >= 2 ? fyKeys[fyKeys.length - 2] : null;
          const currFY = fyKeys.length >= 1 ? fyKeys[fyKeys.length - 1] : null;

          return (
            <Card
              key={idx}
              className="border-l-4 border-l-green-500 cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => handleCategoryClick(category.category_id)}
            >
              <CardContent className="pt-6">
                <div className="space-y-4">
                  {/* Category Header */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">
                      {category.category} - Off-Peak Contracting
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Peak spending in {category.peak_month}, low in{" "}
                      {category.low_month}. Seasonality strength:{" "}
                      {category.seasonality_strength.toFixed(1)}%
                    </p>

                    {/* YoY Growth Badge */}
                    {recentYears.length >= 2 && prevFY && currFY && (
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          YoY Growth ({prevFY} → {currFY}):
                        </span>
                        <Badge
                          variant={
                            category.yoy_growth >= 0 ? "default" : "destructive"
                          }
                          className="gap-1"
                        >
                          {category.yoy_growth >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {category.yoy_growth >= 0 ? "+" : ""}
                          {category.yoy_growth.toFixed(1)}%
                        </Badge>
                        <span className="text-sm text-gray-500 dark:text-gray-500">
                          ${(category.fy_totals[prevFY] ?? 0).toLocaleString()}{" "}
                          → $
                          {(category.fy_totals[currFY] ?? 0).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Metrics Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="bg-cyan-50 dark:bg-cyan-900/30">
                      <CardContent className="pt-4 text-center">
                        <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-400">
                          $
                          {category.savings_potential.toLocaleString(
                            undefined,
                            {
                              minimumFractionDigits: 0,
                              maximumFractionDigits: 0,
                            },
                          )}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          Savings Potential
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-cyan-50 dark:bg-cyan-900/30">
                      <CardContent className="pt-4 text-center">
                        <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-400">
                          {category.impact_level}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          Impact Level
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-cyan-50 dark:bg-cyan-900/30">
                      <CardContent className="pt-4 text-center">
                        <div className="text-2xl font-bold text-cyan-700 dark:text-cyan-400">
                          6-12 months
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          Timeline
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Recommendation */}
                  <div className="bg-yellow-50 dark:bg-yellow-900/30 border-l-4 border-l-yellow-400 p-4 rounded">
                    <div className="flex items-start gap-2">
                      <Lightbulb className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        Contract during {category.low_month} (low demand) for{" "}
                        {category.peak_month} (peak demand) services to optimize
                        costs.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {categorySeasonality.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-gray-600 dark:text-gray-400">
              No significant seasonal patterns detected in the current data. Try
              adjusting filters or uploading more historical data.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Category Drill-Down Modal */}
      <Dialog
        open={selectedCategoryId !== null}
        onOpenChange={(open) => !open && setSelectedCategoryId(null)}
      >
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-purple-600" />
                {drilldownData?.category ?? "Category"} - Supplier Seasonality
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedCategoryId(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>

          {drilldownLoading ? (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
              <Skeleton className="h-[200px] w-full" />
              <Skeleton className="h-[300px] w-full" />
            </div>
          ) : drilldownData ? (
            <div className="space-y-6 py-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="bg-blue-50 dark:bg-blue-900/30">
                  <CardContent className="pt-4 text-center">
                    <DollarSign className="h-6 w-6 mx-auto text-blue-600 dark:text-blue-400 mb-1" />
                    <div className="text-xl font-bold text-blue-700 dark:text-blue-400">
                      ${drilldownData.total_spend.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Total Spend
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-green-50 dark:bg-green-900/30">
                  <CardContent className="pt-4 text-center">
                    <Users className="h-6 w-6 mx-auto text-green-600 dark:text-green-400 mb-1" />
                    <div className="text-xl font-bold text-green-700 dark:text-green-400">
                      {drilldownData.supplier_count}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Suppliers
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-purple-50 dark:bg-purple-900/30">
                  <CardContent className="pt-4 text-center">
                    <BarChart3 className="h-6 w-6 mx-auto text-purple-600 dark:text-purple-400 mb-1" />
                    <div className="text-xl font-bold text-purple-700 dark:text-purple-400">
                      $
                      {Math.round(
                        drilldownData.total_spend /
                          drilldownData.supplier_count,
                      ).toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      Avg/Supplier
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Monthly Totals Bar Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Monthly Spend Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={drilldownData.monthly_totals}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="month"
                        stroke="#6b7280"
                        style={{ fontSize: "11px" }}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: "11px" }}
                        tickFormatter={(value) =>
                          `$${(value / 1000).toFixed(0)}K`
                        }
                      />
                      <Tooltip
                        formatter={(value: number) =>
                          `$${value.toLocaleString()}`
                        }
                        contentStyle={{
                          backgroundColor: "white",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar
                        dataKey="spend"
                        fill="#8b5cf6"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Suppliers Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Top Suppliers by Spend
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b dark:border-gray-700">
                          <th className="text-left p-2 font-semibold">
                            Supplier
                          </th>
                          <th className="text-right p-2 font-semibold">
                            Total Spend
                          </th>
                          <th className="text-right p-2 font-semibold">
                            % of Category
                          </th>
                          <th className="text-center p-2 font-semibold">
                            Peak
                          </th>
                          <th className="text-center p-2 font-semibold">Low</th>
                          <th className="text-right p-2 font-semibold">
                            Seasonality
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {drilldownData.suppliers
                          .slice(0, 10)
                          .map((supplier, idx) => (
                            <tr
                              key={idx}
                              className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                            >
                              <td
                                className="p-2 font-medium truncate max-w-[200px]"
                                title={supplier.name}
                              >
                                {supplier.name}
                              </td>
                              <td className="p-2 text-right">
                                ${supplier.total_spend.toLocaleString()}
                              </td>
                              <td className="p-2 text-right">
                                {supplier.percent_of_category.toFixed(1)}%
                              </td>
                              <td className="p-2 text-center">
                                <Badge
                                  variant="outline"
                                  className="bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                                >
                                  {supplier.peak_month}
                                </Badge>
                              </td>
                              <td className="p-2 text-center">
                                <Badge
                                  variant="outline"
                                  className="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                                >
                                  {supplier.low_month}
                                </Badge>
                              </td>
                              <td className="p-2 text-right">
                                <span
                                  className={
                                    supplier.seasonality_strength > 30
                                      ? "text-red-600 font-medium"
                                      : supplier.seasonality_strength > 20
                                        ? "text-orange-600"
                                        : "text-green-600"
                                  }
                                >
                                  {supplier.seasonality_strength.toFixed(1)}%
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                    {drilldownData.suppliers.length > 10 && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 text-center">
                        Showing top 10 of {drilldownData.suppliers.length}{" "}
                        suppliers
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              No data available for this category.
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
