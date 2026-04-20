import { useState } from "react";
import { useParetoAnalysis, useSupplierDrilldown } from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ComposedChart,
  Bar,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp,
  Target,
  AlertTriangle,
  DollarSign,
  Package,
  MapPin,
  Calendar,
  Loader2,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";

export default function ParetoAnalysis() {
  // Use backend API for accurate Pareto analysis (no data truncation)
  const { data: paretoData = [], isLoading: paretoLoading } =
    useParetoAnalysis();
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(
    null,
  );

  // Fetch supplier drill-down data when a supplier is selected
  const { data: drilldownData, isLoading: drilldownLoading } =
    useSupplierDrilldown(selectedSupplierId);

  // Loading state
  if (paretoLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonChart height={400} type="bar" />
      </div>
    );
  }

  if (paretoData.length === 0) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <TrendingUp className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload your procurement data to see Pareto analysis.
          </p>
        </div>
      </div>
    );
  }

  // Transform backend Pareto data to match the expected format
  // Backend returns: { supplier, supplier_id, amount, cumulative_percentage }
  const totalSpend = paretoData.reduce((sum, item) => sum + item.amount, 0);

  const suppliersWithCumulative = paretoData.map((item, index) => {
    const percentage = totalSpend > 0 ? (item.amount / totalSpend) * 100 : 0;
    const cumulativePercentage = item.cumulative_percentage;

    // Determine classification and priority
    let classification: string;
    let priority: string;
    let recommendedAction: string;

    if (cumulativePercentage <= 80) {
      classification = "Critical (80%)";
      priority = "Strategic";
      recommendedAction = "Partnership Development";
    } else if (cumulativePercentage <= 90) {
      classification = "Important (90%)";
      priority = "Tactical";
      recommendedAction = "Performance Monitoring";
    } else if (cumulativePercentage <= 95) {
      classification = "Standard";
      priority = "Operational";
      recommendedAction = "Regular Review";
    } else {
      classification = "Low Impact";
      priority = "Minimal";
      recommendedAction = "Consolidation Review";
    }

    return {
      rank: index + 1,
      supplier: item.supplier,
      supplierId: item.supplier_id,
      spend: item.amount,
      percentage,
      cumulativePercentage,
      classification,
      priority,
      recommendedAction,
    };
  });

  // Calculate key metrics from backend data
  const suppliersFor80 = suppliersWithCumulative.filter(
    (s) => s.cumulativePercentage <= 80,
  ).length;
  const suppliersFor90 = suppliersWithCumulative.filter(
    (s) => s.cumulativePercentage <= 90,
  ).length;
  const efficiencyRatio =
    paretoData.length > 0 ? (suppliersFor80 / paretoData.length) * 100 : 0;
  const topSupplierShare =
    paretoData.length > 0 && totalSpend > 0
      ? (paretoData[0].amount / totalSpend) * 100
      : 0;

  // Prepare chart data (top 20 suppliers)
  const chartData = suppliersWithCumulative.slice(0, 20).map((s) => ({
    name:
      s.supplier.length > 15 ? s.supplier.substring(0, 15) + "..." : s.supplier,
    fullName: s.supplier,
    supplierId: s.supplierId,
    spend: s.spend,
    cumulative: parseFloat(s.cumulativePercentage.toFixed(1)),
  }));

  // Get classification badge color
  const getClassificationColor = (classification: string) => {
    if (classification.includes("Critical"))
      return "bg-red-100 text-red-800 border-red-200";
    if (classification.includes("Important"))
      return "bg-orange-100 text-orange-800 border-orange-200";
    if (classification.includes("Standard"))
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    return "bg-gray-100 text-gray-800 border-gray-200";
  };

  const COLORS = [
    "#3b82f6",
    "#8b5cf6",
    "#ec4899",
    "#f59e0b",
    "#10b981",
    "#06b6d4",
    "#6366f1",
    "#f97316",
    "#14b8a6",
    "#a855f7",
  ];

  return (
    <div className="space-y-6 p-6">
      {/* Insights & Interpretation Card */}
      <Card className="border-0 shadow-lg bg-gradient-to-br from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Target className="h-6 w-6 text-amber-600" />
            <CardTitle className="text-amber-900 dark:text-amber-100">
              Pareto Analysis Insights & Interpretation
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-amber-100 dark:border-amber-800">
              <div className="text-3xl font-bold text-amber-900 dark:text-amber-100">
                {suppliersFor80}
              </div>
              <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Suppliers (80% spend)
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-amber-100 dark:border-amber-800">
              <div className="text-3xl font-bold text-amber-900 dark:text-amber-100">
                {efficiencyRatio.toFixed(1)}%
              </div>
              <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Efficiency Ratio
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-amber-100 dark:border-amber-800">
              <div className="text-3xl font-bold text-amber-900 dark:text-amber-100">
                {topSupplierShare.toFixed(1)}%
              </div>
              <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Top Supplier Share
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-amber-100 dark:border-amber-800">
              <div className="text-3xl font-bold text-amber-900 dark:text-amber-100">
                {suppliersFor90}
              </div>
              <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Suppliers (90% spend)
              </div>
            </div>
          </div>

          {/* Strategic Analysis */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-amber-100 dark:border-amber-800">
            <div className="flex items-start gap-2 mb-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
              <h3 className="font-bold text-amber-900 dark:text-amber-100">
                Strategic Analysis & Recommendations
              </h3>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
              <span className="font-semibold">
                Excellent Pareto Distribution:
              </span>{" "}
              Only {efficiencyRatio.toFixed(1)}% of suppliers account for 80% of
              spend, indicating a highly efficient supplier base with strong
              concentration among key partners.{" "}
              <span className="font-semibold text-red-600 dark:text-red-400">
                High Dependency Risk:
              </span>{" "}
              The top supplier represents {topSupplierShare.toFixed(1)}% of
              total spend, creating potential supply chain risk.
            </p>
            <div className="bg-amber-50 dark:bg-amber-900/30 rounded-lg p-4 border border-amber-200 dark:border-amber-700">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold text-amber-900 dark:text-amber-100">
                  Recommended Actions:
                </span>{" "}
                Focus on deepening partnerships with top suppliers and
                implementing strategic supplier development programs. Develop
                alternative suppliers to reduce dependency risk.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Pareto Chart */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-600" />
            <CardTitle>Pareto Analysis (80/20 Rule)</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Click on a bar to see supplier details
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart
              data={chartData}
              margin={{ top: 20, right: 60, left: 60, bottom: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                height={100}
                tick={{ fontSize: 11 }}
                stroke="#6b7280"
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11 }}
                stroke="#6b7280"
                tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                stroke="#6b7280"
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  padding: "12px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
                formatter={(value: number, name: string) => {
                  if (name === "Spend")
                    return [`$${value.toLocaleString()}`, "Spend"];
                  if (name === "Cumulative %")
                    return [`${value.toFixed(1)}%`, "Cumulative %"];
                  return value;
                }}
                labelFormatter={(label) => label}
                labelStyle={{ fontWeight: "bold", marginBottom: "4px" }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                iconType="circle"
                formatter={(value) => (
                  <span style={{ color: "#374151", fontSize: "14px" }}>
                    {value}
                  </span>
                )}
              />
              <Bar
                yAxisId="left"
                dataKey="spend"
                fill="#3b82f6"
                name="Spend"
                radius={[4, 4, 0, 0]}
                cursor="pointer"
                onClick={(data) => {
                  if (data && data.supplierId) {
                    setSelectedSupplierId(data.supplierId);
                  }
                }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative"
                stroke="#8b5cf6"
                strokeWidth={2}
                name="Cumulative %"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Detailed Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Pareto Details with Strategic Recommendations</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-gray-800 text-white sticky top-0">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase">
                    Rank
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase">
                    Supplier
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold uppercase">
                    Spend
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold uppercase">
                    Cumulative %
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-bold uppercase">
                    Classification
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-bold uppercase">
                    Strategic Priority
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase">
                    Recommended Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {suppliersWithCumulative.map((sup) => (
                  <tr
                    key={sup.rank}
                    className="hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-colors cursor-pointer"
                    onClick={() => setSelectedSupplierId(sup.supplierId)}
                  >
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                      #{sup.rank}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                      {sup.supplier}
                    </td>
                    <td className="px-6 py-4 text-sm text-right font-semibold text-gray-900 dark:text-gray-100">
                      $
                      {sup.spend.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-gray-600 dark:text-gray-400">
                      {sup.cumulativePercentage.toFixed(2)}%
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Badge
                        className={`${getClassificationColor(sup.classification)} border`}
                      >
                        {sup.classification}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-center text-gray-700 dark:text-gray-300 font-medium">
                      {sup.priority}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">
                      {sup.recommendedAction}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Supplier Drill-Down Modal */}
      <Dialog
        open={!!selectedSupplierId}
        onOpenChange={() => setSelectedSupplierId(null)}
      >
        <DialogContent className="!max-w-6xl max-h-[90vh] overflow-y-auto">
          {drilldownLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">
                Loading supplier details...
              </span>
            </div>
          ) : drilldownData ? (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl">
                  Supplier Details: {drilldownData.supplier_name}
                </DialogTitle>
              </DialogHeader>

              <div className="space-y-6 mt-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                          <DollarSign className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Total Spend
                          </p>
                          <p className="text-2xl font-bold">
                            ${drilldownData.total_spend.toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                          <Package className="h-6 w-6 text-purple-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Transactions
                          </p>
                          <p className="text-2xl font-bold">
                            {drilldownData.transaction_count}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                          <TrendingUp className="h-6 w-6 text-green-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Avg Transaction
                          </p>
                          <p className="text-2xl font-bold">
                            $
                            {drilldownData.avg_transaction.toLocaleString(
                              undefined,
                              { maximumFractionDigits: 0 },
                            )}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                          <Calendar className="h-6 w-6 text-amber-600" />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Date Range
                          </p>
                          <p className="text-sm font-semibold">
                            {drilldownData.date_range.min
                              ? new Date(
                                  drilldownData.date_range.min,
                                ).toLocaleDateString()
                              : "N/A"}{" "}
                            -{" "}
                            {drilldownData.date_range.max
                              ? new Date(
                                  drilldownData.date_range.max,
                                ).toLocaleDateString()
                              : "N/A"}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Category Breakdown */}
                {drilldownData.categories.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Spending by Category
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={drilldownData.categories}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={100}
                            paddingAngle={2}
                            dataKey="spend"
                            nameKey="name"
                          >
                            {drilldownData.categories.map((_entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={COLORS[index % COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value: number) =>
                              `$${value.toLocaleString()}`
                            }
                          />
                          <Legend
                            layout="vertical"
                            align="right"
                            verticalAlign="middle"
                            formatter={(value) => String(value)}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                )}

                {/* Subcategory Breakdown */}
                {drilldownData.subcategories.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Top 10 Subcategories
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {drilldownData.subcategories.map((item, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between"
                          >
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                  {item.name}
                                </span>
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                  ${item.spend.toLocaleString()} (
                                  {item.percent_of_total.toFixed(1)}%)
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{
                                    width: `${Math.min(item.percent_of_total, 100)}%`,
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Location Breakdown */}
                {drilldownData.locations.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MapPin className="h-5 w-5" />
                        Top 10 Locations
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {drilldownData.locations.map((item, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between"
                          >
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                  {item.name}
                                </span>
                                <span className="text-sm text-gray-600 dark:text-gray-400">
                                  ${item.spend.toLocaleString()} (
                                  {item.percent_of_total.toFixed(1)}%)
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                <div
                                  className="bg-purple-600 h-2 rounded-full"
                                  style={{
                                    width: `${Math.min(item.percent_of_total, 100)}%`,
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center py-12">
              <p className="text-gray-600 dark:text-gray-400">
                No data available for this supplier.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
