import { useState } from "react";
import { useSupplierDetails } from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  BarChart,
  Bar,
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
  Users,
  TrendingUp,
  DollarSign,
  Percent,
  AlertTriangle,
  Shield,
  ShieldAlert,
  Search,
  X,
  Loader2,
} from "lucide-react";

export default function Suppliers() {
  const { data, isLoading, error } = useSupplierDetails();
  const [searchQuery, setSearchQuery] = useState("");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <Loader2 className="h-16 w-16 text-blue-500 mx-auto mb-4 animate-spin" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Loading Supplier Data
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Analyzing supplier metrics...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Error Loading Data
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Failed to load supplier analysis. Please try again.
          </p>
        </div>
      </div>
    );
  }

  if (!data || data.suppliers.length === 0) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <Users className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload your procurement data to see supplier analysis.
          </p>
        </div>
      </div>
    );
  }

  const { summary, suppliers } = data;

  // Filter suppliers based on search query
  const filteredSuppliers = searchQuery.trim()
    ? suppliers.filter((sup) =>
        sup.supplier.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : suppliers;

  // Get HHI risk styling
  const getHHIRiskStyling = (riskLevel: "low" | "moderate" | "high") => {
    if (riskLevel === "low")
      return {
        color: "text-green-600",
        bgColor: "bg-green-50 dark:bg-green-900/20",
        icon: Shield,
      };
    if (riskLevel === "moderate")
      return {
        color: "text-yellow-600",
        bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
        icon: AlertTriangle,
      };
    return {
      color: "text-red-600",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      icon: ShieldAlert,
    };
  };

  const hhiRisk = getHHIRiskStyling(summary.hhi_risk_level);

  // Colors for charts
  const COLORS = [
    "#3b82f6",
    "#8b5cf6",
    "#ec4899",
    "#f59e0b",
    "#10b981",
    "#06b6d4",
    "#6366f1",
    "#f43f5e",
    "#84cc16",
    "#14b8a6",
  ];

  // Prepare data for pie chart (top 10 suppliers)
  const topSuppliers = suppliers.slice(0, 10);
  const pieData = topSuppliers.map((sup) => ({
    name: sup.supplier,
    value: sup.total_spend,
  }));

  // Prepare data for bar chart
  const barData = topSuppliers.map((sup) => ({
    supplier:
      sup.supplier.length > 20
        ? sup.supplier.substring(0, 20) + "..."
        : sup.supplier,
    spend: sup.total_spend,
    transactions: sup.transaction_count,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Supplier Analysis
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Analyze vendor performance and spending patterns
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                Total Suppliers
              </CardTitle>
              <Users className="h-5 w-5 text-blue-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {summary.total_suppliers}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Active vendors
            </p>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                Total Spend
              </CardTitle>
              <DollarSign className="h-5 w-5 text-green-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              ${(summary.total_spend / 1000000).toFixed(1)}M
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Across all suppliers
            </p>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-lg">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                Top Supplier
              </CardTitle>
              <TrendingUp className="h-5 w-5 text-purple-500" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
              {summary.top_supplier || "N/A"}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              ${(summary.top_supplier_spend / 1000).toFixed(0)}K spend
            </p>
          </CardContent>
        </Card>

        <Card
          className={`border-0 shadow-lg ${summary.top3_concentration > 50 ? "bg-red-50 dark:bg-red-900/20" : ""}`}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                Concentration Risk
              </CardTitle>
              {summary.top3_concentration > 50 ? (
                <AlertTriangle className="h-5 w-5 text-red-500" />
              ) : (
                <Percent className="h-5 w-5 text-orange-500" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div
              className={`text-3xl font-bold ${summary.top3_concentration > 50 ? "text-red-600" : "text-gray-900 dark:text-gray-100"}`}
            >
              {summary.top3_concentration.toFixed(1)}%
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Top 3 suppliers
            </p>
          </CardContent>
        </Card>

        <Card className={`border-0 shadow-lg ${hhiRisk.bgColor}`}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                HHI Score
              </CardTitle>
              <hhiRisk.icon className={`h-5 w-5 ${hhiRisk.color}`} />
            </div>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${hhiRisk.color}`}>
              {summary.hhi_score.toFixed(0)}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span className={`font-semibold ${hhiRisk.color}`}>
                {summary.hhi_risk_level.charAt(0).toUpperCase() +
                  summary.hhi_risk_level.slice(1)}
              </span>{" "}
              concentration
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>Spend Distribution by Supplier</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                  label={false}
                >
                  {pieData.map((_entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => `$${value.toLocaleString()}`}
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid #e5e7eb",
                    borderRadius: "6px",
                    padding: "8px",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={60}
                  iconType="circle"
                  wrapperStyle={{ fontSize: "12px" }}
                  formatter={(value) =>
                    value.length > 30 ? value.substring(0, 30) + "..." : value
                  }
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Bar Chart */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>Top 10 Suppliers by Spend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={barData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                />
                <YAxis type="category" dataKey="supplier" width={150} />
                <Tooltip
                  formatter={(value: number) => `$${value.toLocaleString()}`}
                />
                <Bar dataKey="spend" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Supplier Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Supplier Details</CardTitle>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {searchQuery && (
                <span>
                  {filteredSuppliers.length} of {suppliers.length} suppliers
                </span>
              )}
            </div>
          </div>
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search suppliers by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-10"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Rank
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Supplier
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Total Spend
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    % of Total
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Transactions
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Avg Transaction
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                    Categories
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {filteredSuppliers.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center">
                      <Search className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500 dark:text-gray-400 font-medium">
                        No suppliers found
                      </p>
                      <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                        Try adjusting your search query
                      </p>
                    </td>
                  </tr>
                ) : (
                  filteredSuppliers.map((sup) => (
                    <tr
                      key={sup.supplier_id}
                      className="hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-colors"
                    >
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                        {sup.rank}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                        {sup.supplier}
                      </td>
                      <td className="px-6 py-4 text-sm text-right font-semibold text-gray-900 dark:text-gray-100">
                        $
                        {sup.total_spend.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-600 dark:text-gray-400">
                        {sup.percent_of_total.toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-600 dark:text-gray-400">
                        {sup.transaction_count.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-600 dark:text-gray-400">
                        $
                        {sup.avg_transaction.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-600 dark:text-gray-400">
                        {sup.category_count}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
