import { useState } from "react";
import {
  useDetailedYearOverYear,
  useYoYCategoryDrilldown,
  useYoYSupplierDrilldown,
} from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingCart,
  Users,
  Calculator,
  ArrowUp,
  ArrowDown,
  BarChart3,
  X,
  Calendar,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from "recharts";

const COLORS = [
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#f59e0b",
  "#10b981",
  "#06b6d4",
  "#f97316",
  "#6366f1",
];

export default function YearOverYear() {
  const [useFiscalYear, setUseFiscalYear] = useState(true);
  const [year1Override, setYear1Override] = useState<number | undefined>(
    undefined,
  );
  const [year2Override, setYear2Override] = useState<number | undefined>(
    undefined,
  );
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null,
  );
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(
    null,
  );

  // Fetch data from backend
  const { data, isLoading, error } = useDetailedYearOverYear(
    useFiscalYear,
    year1Override,
    year2Override,
  );

  // Fetch drill-down data when category/supplier selected
  const { data: categoryDrilldown, isLoading: categoryDrilldownLoading } =
    useYoYCategoryDrilldown(
      selectedCategoryId,
      useFiscalYear,
      year1Override,
      year2Override,
    );
  const { data: supplierDrilldown, isLoading: supplierDrilldownLoading } =
    useYoYSupplierDrilldown(
      selectedSupplierId,
      useFiscalYear,
      year1Override,
      year2Override,
    );

  // Create color map for categories
  const categoryColorMap: Record<string, string> = {};
  if (data?.category_comparison) {
    data.category_comparison.forEach((cat, idx) => {
      categoryColorMap[cat.category] = COLORS[idx % COLORS.length];
    });
  }

  // Prepare chart data
  const fy1ChartData =
    data?.category_comparison
      ?.map((cat) => ({
        name: cat.category,
        value: cat.year1_spend,
        color: categoryColorMap[cat.category],
      }))
      .filter((d) => d.value > 0) || [];

  const fy2ChartData =
    data?.category_comparison
      ?.map((cat) => ({
        name: cat.category,
        value: cat.year2_spend,
        color: categoryColorMap[cat.category],
      }))
      .filter((d) => d.value > 0) || [];

  // Category growth data for bar chart
  const categoryGrowthData =
    data?.category_comparison
      ?.filter((cat) => cat.year1_spend > 0 && cat.year2_spend > 0)
      .map((cat) => ({
        category: cat.category,
        category_id: cat.category_id,
        growth: cat.change_pct,
      }))
      .sort((a, b) => Math.abs(b.growth) - Math.abs(a.growth))
      .slice(0, 10) || [];

  // Monthly chart data
  const monthlyChartData =
    data?.monthly_comparison?.map((m) => ({
      month: m.month,
      [data.summary.year1]: m.year1_spend,
      [data.summary.year2]: m.year2_spend,
    })) || [];

  // MoM growth data
  const momGrowthData =
    data?.monthly_comparison?.map((m) => ({
      month: m.month,
      growth: m.change_pct,
    })) || [];

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-10 w-96" />
        </div>
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-6">
          <Skeleton className="h-[400px] w-full" />
          <Skeleton className="h-[400px] w-full" />
        </div>
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          Year-over-Year Analysis
        </h1>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-gray-600 dark:text-gray-400">
              {error
                ? "Failed to load data. Please try again."
                : "No data available for year-over-year analysis."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const {
    summary,
    monthly_comparison,
    category_comparison,
    supplier_comparison,
    top_gainers,
    top_decliners,
    available_years,
  } = data;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Year-over-Year Analysis
        </h1>

        <div className="flex items-center gap-4 flex-wrap">
          {/* Fiscal Year Toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="fiscalYear"
              checked={useFiscalYear}
              onCheckedChange={(checked) =>
                setUseFiscalYear(checked as boolean)
              }
            />
            <label
              htmlFor="fiscalYear"
              className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
            >
              Use Fiscal Year (Jul-Jun)
            </label>
          </div>

          {/* Year Selectors */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Compare:
            </label>
            <Select
              value={year1Override?.toString() || "auto"}
              onValueChange={(value) =>
                setYear1Override(value === "auto" ? undefined : parseInt(value))
              }
            >
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto</SelectItem>
                {available_years.map((year) => (
                  <SelectItem key={year} value={year.toString()}>
                    {useFiscalYear ? `FY${year}` : year.toString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-gray-600 dark:text-gray-400">vs</span>
            <Select
              value={year2Override?.toString() || "auto"}
              onValueChange={(value) =>
                setYear2Override(value === "auto" ? undefined : parseInt(value))
              }
            >
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto</SelectItem>
                {available_years.map((year) => (
                  <SelectItem key={year} value={year.toString()}>
                    {useFiscalYear ? `FY${year}` : year.toString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Key Metrics Comparison */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg mb-3">
                <DollarSign className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              </div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Total Spend
              </p>
              <div className="flex items-center justify-center gap-4 mb-2 w-full">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year2}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    $
                    {summary.year2_total_spend.toLocaleString(undefined, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year1}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    $
                    {summary.year1_total_spend.toLocaleString(undefined, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
              </div>
              <div
                className={`flex items-center gap-1 text-sm font-bold ${summary.spend_change_pct >= 0 ? "text-green-600" : "text-red-600"}`}
              >
                {summary.spend_change_pct >= 0 ? (
                  <ArrowUp className="h-4 w-4" />
                ) : (
                  <ArrowDown className="h-4 w-4" />
                )}
                {summary.spend_change_pct >= 0 ? "+" : ""}
                {summary.spend_change_pct.toFixed(1)}%
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {summary.spend_change >= 0 ? "+" : ""}$
                {summary.spend_change.toLocaleString(undefined, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}{" "}
                change
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg mb-3">
                <ShoppingCart className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              </div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Transaction Count
              </p>
              <div className="flex items-center justify-center gap-4 mb-2 w-full">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year2}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {summary.year2_transactions.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year1}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {summary.year1_transactions.toLocaleString()}
                  </p>
                </div>
              </div>
              {summary.year1_transactions > 0 && (
                <>
                  <div
                    className={`flex items-center gap-1 text-sm font-bold ${
                      summary.year2_transactions - summary.year1_transactions >=
                      0
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {summary.year2_transactions - summary.year1_transactions >=
                    0 ? (
                      <ArrowUp className="h-4 w-4" />
                    ) : (
                      <ArrowDown className="h-4 w-4" />
                    )}
                    {(
                      ((summary.year2_transactions -
                        summary.year1_transactions) /
                        summary.year1_transactions) *
                      100
                    ).toFixed(1)}
                    %
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {summary.year2_transactions - summary.year1_transactions >=
                    0
                      ? "+"
                      : ""}
                    {(
                      summary.year2_transactions - summary.year1_transactions
                    ).toLocaleString()}{" "}
                    change
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg mb-3">
                <Calculator className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Average Transaction
              </p>
              <div className="flex items-center justify-center gap-4 mb-2 w-full">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year2}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    $
                    {summary.year2_avg_transaction.toLocaleString(undefined, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year1}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    $
                    {summary.year1_avg_transaction.toLocaleString(undefined, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
              </div>
              {summary.year1_avg_transaction > 0 && (
                <>
                  <div
                    className={`flex items-center gap-1 text-sm font-bold ${
                      summary.year2_avg_transaction -
                        summary.year1_avg_transaction >=
                      0
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {summary.year2_avg_transaction -
                      summary.year1_avg_transaction >=
                    0 ? (
                      <ArrowUp className="h-4 w-4" />
                    ) : (
                      <ArrowDown className="h-4 w-4" />
                    )}
                    {(
                      ((summary.year2_avg_transaction -
                        summary.year1_avg_transaction) /
                        summary.year1_avg_transaction) *
                      100
                    ).toFixed(1)}
                    %
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {summary.year2_avg_transaction -
                      summary.year1_avg_transaction >=
                    0
                      ? "+"
                      : ""}
                    $
                    {(
                      summary.year2_avg_transaction -
                      summary.year1_avg_transaction
                    ).toLocaleString(undefined, {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}{" "}
                    change
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg mb-3">
                <Users className="h-8 w-8 text-orange-600 dark:text-orange-400" />
              </div>
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Supplier Count
              </p>
              <div className="flex items-center justify-center gap-4 mb-2 w-full">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year2}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {summary.year2_suppliers.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {summary.year1}
                  </p>
                  <p className="text-base font-bold text-gray-900 dark:text-gray-100">
                    {summary.year1_suppliers.toLocaleString()}
                  </p>
                </div>
              </div>
              {summary.year1_suppliers > 0 && (
                <>
                  <div
                    className={`flex items-center gap-1 text-sm font-bold ${
                      summary.year2_suppliers - summary.year1_suppliers >= 0
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {summary.year2_suppliers - summary.year1_suppliers >= 0 ? (
                      <ArrowUp className="h-4 w-4" />
                    ) : (
                      <ArrowDown className="h-4 w-4" />
                    )}
                    {(
                      ((summary.year2_suppliers - summary.year1_suppliers) /
                        summary.year1_suppliers) *
                      100
                    ).toFixed(1)}
                    %
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {summary.year2_suppliers - summary.year1_suppliers >= 0
                      ? "+"
                      : ""}
                    {(
                      summary.year2_suppliers - summary.year1_suppliers
                    ).toLocaleString()}{" "}
                    change
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Comparison */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          Category Comparison
          <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
            (Click chart or table rows for details)
          </span>
        </h2>
        <div className="grid grid-cols-2 gap-6">
          {/* Year 1 Distribution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">
                {summary.year1} Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-8">
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={fy1ChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    paddingAngle={2}
                    dataKey="value"
                    onClick={(entry) => {
                      const cat = category_comparison.find(
                        (c) => c.category === entry.name,
                      );
                      if (cat?.category_id)
                        setSelectedCategoryId(cat.category_id);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    {fy1ChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
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
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Year 2 Distribution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">
                {summary.year2} Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-8">
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={fy2ChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    paddingAngle={2}
                    dataKey="value"
                    onClick={(entry) => {
                      const cat = category_comparison.find(
                        (c) => c.category === entry.name,
                      );
                      if (cat?.category_id)
                        setSelectedCategoryId(cat.category_id);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    {fy2ChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
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
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Shared Legend */}
        <div className="mt-6 flex flex-wrap justify-center gap-x-6 gap-y-2">
          {Object.entries(categoryColorMap).map(([category, color]) => (
            <div key={category} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {category}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Category Growth Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Category Spend Analysis (Sorted by Growth %)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={categoryGrowthData}
              layout="vertical"
              onClick={(e) => {
                if (e?.activePayload?.[0]?.payload?.category_id) {
                  setSelectedCategoryId(e.activePayload[0].payload.category_id);
                }
              }}
              style={{ cursor: "pointer" }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                type="number"
                tickFormatter={(value) => `${value.toFixed(0)}%`}
              />
              <YAxis
                type="category"
                dataKey="category"
                width={200}
                style={{ fontSize: "12px" }}
              />
              <Tooltip
                formatter={(value: number) => `${value.toFixed(1)}%`}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
              />
              <Bar dataKey="growth" fill="#3b82f6">
                {categoryGrowthData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.growth >= 0 ? "#10b981" : "#ef4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Monthly Spending Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            Monthly Spending Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={monthlyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="month"
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
                tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
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
              <Legend />
              <Line
                type="monotone"
                dataKey={summary.year1}
                stroke="#06b6d4"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey={summary.year2}
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Month-over-Month Growth Rate */}
      <Card>
        <CardHeader>
          <CardTitle>Month-over-Month Growth Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={momGrowthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="month"
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: "12px" }}
                tickFormatter={(value) => `${value.toFixed(0)}%`}
              />
              <Tooltip
                formatter={(value: number) => `${value.toFixed(1)}%`}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
              />
              <Bar dataKey="growth">
                {momGrowthData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.growth >= 0 ? "#10b981" : "#ef4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top Movers */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Gainers */}
        <Card className="border-l-4 border-l-green-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
              <TrendingUp className="h-5 w-5" />
              Top Gainers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {top_gainers.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No categories with positive growth
                </p>
              ) : (
                top_gainers.map((item, idx) => (
                  <div
                    key={idx}
                    className="border-b border-gray-200 dark:border-gray-700 pb-3 last:border-0 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 -mx-2 px-2 py-1 rounded transition-colors"
                    onClick={() =>
                      item.category_id &&
                      setSelectedCategoryId(item.category_id)
                    }
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 dark:text-gray-100">
                          {item.category}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          Current: $
                          {item.year2_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-500">
                          Previous: $
                          {item.year1_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-green-600 font-bold">
                          <ArrowUp className="h-4 w-4" />+
                          {item.change_pct.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Decliners */}
        <Card className="border-l-4 border-l-red-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700 dark:text-red-400">
              <TrendingDown className="h-5 w-5" />
              Top Decliners
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {top_decliners.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No categories with negative growth
                </p>
              ) : (
                top_decliners.map((item, idx) => (
                  <div
                    key={idx}
                    className="border-b border-gray-200 dark:border-gray-700 pb-3 last:border-0 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 -mx-2 px-2 py-1 rounded transition-colors"
                    onClick={() =>
                      item.category_id &&
                      setSelectedCategoryId(item.category_id)
                    }
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 dark:text-gray-100">
                          {item.category}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          Current: $
                          {item.year2_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-500">
                          Previous: $
                          {item.year1_spend.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-red-600 font-bold">
                          <ArrowDown className="h-4 w-4" />
                          {item.change_pct.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Suppliers Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            Top Suppliers Comparison
            <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
              (Click row for details)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Supplier Name
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    {summary.year1} Spend
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    {summary.year2} Spend
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Change
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Growth %
                  </th>
                </tr>
              </thead>
              <tbody>
                {supplier_comparison.slice(0, 15).map((item, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
                    onClick={() =>
                      item.supplier_id &&
                      setSelectedSupplierId(item.supplier_id)
                    }
                  >
                    <td className="py-3 px-4 text-gray-900 dark:text-gray-100">
                      {item.supplier}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      $
                      {item.year1_spend.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      $
                      {item.year2_spend.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </td>
                    <td
                      className={`py-3 px-4 text-right font-medium ${item.change >= 0 ? "text-green-600" : "text-red-600"}`}
                    >
                      {item.change >= 0 ? "+" : ""}$
                      {item.change.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div
                        className={`flex items-center justify-end gap-1 font-bold ${item.change_pct >= 0 ? "text-green-600" : "text-red-600"}`}
                      >
                        {item.change_pct >= 0 ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )}
                        {item.change_pct >= 0 ? "+" : ""}
                        {item.change_pct.toFixed(1)}%
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

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
                {categoryDrilldown?.category ?? "Category"} - YoY Breakdown
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedCategoryId(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
            <DialogDescription className="sr-only">
              Year-over-year spending breakdown for the selected category
              showing supplier details and monthly trends.
            </DialogDescription>
          </DialogHeader>

          {categoryDrilldownLoading ? (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
              <Skeleton className="h-[200px] w-full" />
              <Skeleton className="h-[300px] w-full" />
            </div>
          ) : categoryDrilldown ? (
            <div className="space-y-6 py-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="bg-blue-50 dark:bg-blue-900/30">
                  <CardContent className="pt-4 text-center">
                    <DollarSign className="h-6 w-6 mx-auto text-blue-600 dark:text-blue-400 mb-1" />
                    <div className="text-xl font-bold text-blue-700 dark:text-blue-400">
                      ${categoryDrilldown.year2_total.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {categoryDrilldown.year2} Spend
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-green-50 dark:bg-green-900/30">
                  <CardContent className="pt-4 text-center">
                    <DollarSign className="h-6 w-6 mx-auto text-green-600 dark:text-green-400 mb-1" />
                    <div className="text-xl font-bold text-green-700 dark:text-green-400">
                      ${categoryDrilldown.year1_total.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {categoryDrilldown.year1} Spend
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={
                    categoryDrilldown.change_pct >= 0
                      ? "bg-emerald-50 dark:bg-emerald-900/30"
                      : "bg-red-50 dark:bg-red-900/30"
                  }
                >
                  <CardContent className="pt-4 text-center">
                    {categoryDrilldown.change_pct >= 0 ? (
                      <TrendingUp className="h-6 w-6 mx-auto text-emerald-600 dark:text-emerald-400 mb-1" />
                    ) : (
                      <TrendingDown className="h-6 w-6 mx-auto text-red-600 dark:text-red-400 mb-1" />
                    )}
                    <div
                      className={`text-xl font-bold ${categoryDrilldown.change_pct >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"}`}
                    >
                      {categoryDrilldown.change_pct >= 0 ? "+" : ""}
                      {categoryDrilldown.change_pct.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      YoY Change
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Monthly Breakdown Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Monthly Spend Comparison
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={categoryDrilldown.monthly_breakdown}>
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
                        formatter={(value: number, name: string) => [
                          `$${value.toLocaleString()}`,
                          name,
                        ]}
                        contentStyle={{
                          backgroundColor: "white",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Bar
                        dataKey="year1_spend"
                        name={categoryDrilldown.year1}
                        fill="#06b6d4"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="year2_spend"
                        name={categoryDrilldown.year2}
                        fill="#10b981"
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
                    Suppliers in Category
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
                            {categoryDrilldown.year1}
                          </th>
                          <th className="text-right p-2 font-semibold">
                            {categoryDrilldown.year2}
                          </th>
                          <th className="text-right p-2 font-semibold">
                            Change
                          </th>
                          <th className="text-right p-2 font-semibold">
                            Growth
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {categoryDrilldown.suppliers
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
                                ${supplier.year1_spend.toLocaleString()}
                              </td>
                              <td className="p-2 text-right">
                                ${supplier.year2_spend.toLocaleString()}
                              </td>
                              <td
                                className={`p-2 text-right ${supplier.change >= 0 ? "text-green-600" : "text-red-600"}`}
                              >
                                {supplier.change >= 0 ? "+" : ""}$
                                {supplier.change.toLocaleString()}
                              </td>
                              <td className="p-2 text-right">
                                <Badge
                                  variant={
                                    supplier.change_pct >= 0
                                      ? "default"
                                      : "destructive"
                                  }
                                  className="gap-1"
                                >
                                  {supplier.change_pct >= 0 ? (
                                    <ArrowUp className="h-3 w-3" />
                                  ) : (
                                    <ArrowDown className="h-3 w-3" />
                                  )}
                                  {supplier.change_pct.toFixed(1)}%
                                </Badge>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                    {categoryDrilldown.suppliers.length > 10 && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 text-center">
                        Showing top 10 of {categoryDrilldown.suppliers.length}{" "}
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

      {/* Supplier Drill-Down Modal */}
      <Dialog
        open={selectedSupplierId !== null}
        onOpenChange={(open) => !open && setSelectedSupplierId(null)}
      >
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Users className="h-5 w-5 text-orange-600" />
                {supplierDrilldown?.supplier ?? "Supplier"} - YoY Breakdown
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedSupplierId(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
            <DialogDescription className="sr-only">
              Year-over-year spending breakdown for the selected supplier
              showing category details and monthly trends.
            </DialogDescription>
          </DialogHeader>

          {supplierDrilldownLoading ? (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
              <Skeleton className="h-[200px] w-full" />
              <Skeleton className="h-[300px] w-full" />
            </div>
          ) : supplierDrilldown ? (
            <div className="space-y-6 py-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="bg-blue-50 dark:bg-blue-900/30">
                  <CardContent className="pt-4 text-center">
                    <DollarSign className="h-6 w-6 mx-auto text-blue-600 dark:text-blue-400 mb-1" />
                    <div className="text-xl font-bold text-blue-700 dark:text-blue-400">
                      ${supplierDrilldown.year2_total.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {supplierDrilldown.year2} Spend
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-green-50 dark:bg-green-900/30">
                  <CardContent className="pt-4 text-center">
                    <DollarSign className="h-6 w-6 mx-auto text-green-600 dark:text-green-400 mb-1" />
                    <div className="text-xl font-bold text-green-700 dark:text-green-400">
                      ${supplierDrilldown.year1_total.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {supplierDrilldown.year1} Spend
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={
                    supplierDrilldown.change_pct >= 0
                      ? "bg-emerald-50 dark:bg-emerald-900/30"
                      : "bg-red-50 dark:bg-red-900/30"
                  }
                >
                  <CardContent className="pt-4 text-center">
                    {supplierDrilldown.change_pct >= 0 ? (
                      <TrendingUp className="h-6 w-6 mx-auto text-emerald-600 dark:text-emerald-400 mb-1" />
                    ) : (
                      <TrendingDown className="h-6 w-6 mx-auto text-red-600 dark:text-red-400 mb-1" />
                    )}
                    <div
                      className={`text-xl font-bold ${supplierDrilldown.change_pct >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"}`}
                    >
                      {supplierDrilldown.change_pct >= 0 ? "+" : ""}
                      {supplierDrilldown.change_pct.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      YoY Change
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Monthly Breakdown Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Monthly Spend Comparison
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={supplierDrilldown.monthly_breakdown}>
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
                        formatter={(value: number, name: string) => [
                          `$${value.toLocaleString()}`,
                          name,
                        ]}
                        contentStyle={{
                          backgroundColor: "white",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Bar
                        dataKey="year1_spend"
                        name={supplierDrilldown.year1}
                        fill="#06b6d4"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="year2_spend"
                        name={supplierDrilldown.year2}
                        fill="#10b981"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Categories Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Categories from Supplier
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b dark:border-gray-700">
                          <th className="text-left p-2 font-semibold">
                            Category
                          </th>
                          <th className="text-right p-2 font-semibold">
                            {supplierDrilldown.year1}
                          </th>
                          <th className="text-right p-2 font-semibold">
                            {supplierDrilldown.year2}
                          </th>
                          <th className="text-right p-2 font-semibold">
                            Change
                          </th>
                          <th className="text-right p-2 font-semibold">
                            Growth
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {supplierDrilldown.categories
                          .slice(0, 10)
                          .map((cat, idx) => (
                            <tr
                              key={idx}
                              className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                            >
                              <td
                                className="p-2 font-medium truncate max-w-[200px]"
                                title={cat.name}
                              >
                                {cat.name}
                              </td>
                              <td className="p-2 text-right">
                                ${cat.year1_spend.toLocaleString()}
                              </td>
                              <td className="p-2 text-right">
                                ${cat.year2_spend.toLocaleString()}
                              </td>
                              <td
                                className={`p-2 text-right ${cat.change >= 0 ? "text-green-600" : "text-red-600"}`}
                              >
                                {cat.change >= 0 ? "+" : ""}$
                                {cat.change.toLocaleString()}
                              </td>
                              <td className="p-2 text-right">
                                <Badge
                                  variant={
                                    cat.change_pct >= 0
                                      ? "default"
                                      : "destructive"
                                  }
                                  className="gap-1"
                                >
                                  {cat.change_pct >= 0 ? (
                                    <ArrowUp className="h-3 w-3" />
                                  ) : (
                                    <ArrowDown className="h-3 w-3" />
                                  )}
                                  {cat.change_pct.toFixed(1)}%
                                </Badge>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                    {supplierDrilldown.categories.length > 10 && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 text-center">
                        Showing top 10 of {supplierDrilldown.categories.length}{" "}
                        categories
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              No data available for this supplier.
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
