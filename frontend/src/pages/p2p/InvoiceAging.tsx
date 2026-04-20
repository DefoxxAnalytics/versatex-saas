import { useState } from "react";
import {
  useAgingOverview,
  useAgingBySupplier,
  usePaymentTermsCompliance,
  useDPOTrends,
  useCashFlowForecast,
} from "@/hooks/useP2PAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  type TooltipProps,
} from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  Clock,
  DollarSign,
  Calendar,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Building2,
  Percent,
  Wallet,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import { cn } from "@/lib/utils";

// Custom tooltip for aging bucket chart
interface AgingBucketData {
  name: string;
  amount: number;
  count: number;
  percent: number;
  color: string;
}

const AgingBucketTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as AgingBucketData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Amount: {formatCurrency(data.amount)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Invoices: {data.count?.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        % of Total: {data.percent?.toFixed(1)}%
      </div>
    </div>
  );
};

// Custom tooltip for supplier aging chart
interface SupplierAgingData {
  name: string;
  fullName: string;
  current: number;
  overdue: number;
  total: number;
  daysOverdue: number;
}

const SupplierAgingTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as SupplierAgingData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Total AP: {formatCurrency(data.total)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Current: {formatCurrency(data.current)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Overdue: {formatCurrency(data.overdue)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Avg Days: {data.daysOverdue?.toFixed(0)}
      </div>
    </div>
  );
};

// Custom tooltip for payment terms compliance chart
interface PaymentTermsData {
  name: string;
  onTime: number;
  late: number;
  count: number;
  discountCaptured: number;
}

const PaymentTermsTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as PaymentTermsData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        On Time: {data.onTime.toFixed(1)}%
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Late: {data.late.toFixed(1)}%
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Invoices: {data.count?.toLocaleString()}
      </div>
      {data.discountCaptured > 0 && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Discount Captured: {data.discountCaptured?.toFixed(1)}%
        </div>
      )}
    </div>
  );
};

/**
 * Invoice Aging & AP Dashboard - Accounts Payable aging and payment analysis
 * Shows aging buckets, DPO, payment terms compliance, and cash flow forecasts
 */
export default function InvoiceAging() {
  const { data: agingOverview, isLoading: overviewLoading } =
    useAgingOverview();
  const { data: agingBySupplier, isLoading: supplierLoading } =
    useAgingBySupplier();
  const { data: paymentTerms, isLoading: termsLoading } =
    usePaymentTermsCompliance();
  const { data: dpoTrends, isLoading: dpoLoading } = useDPOTrends(12);
  const { data: cashForecast, isLoading: forecastLoading } =
    useCashFlowForecast(8);

  const isLoading =
    overviewLoading ||
    supplierLoading ||
    termsLoading ||
    dpoLoading ||
    forecastLoading;

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonChart height={350} type="bar" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart height={300} type="line" />
          <SkeletonChart height={300} type="area" />
        </div>
      </div>
    );
  }

  // No data state
  if (!agingOverview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <Clock className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No AP Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload invoice data to see aging analysis.
          </p>
        </div>
      </div>
    );
  }

  // Calculate overdue amount from buckets (31-60, 61-90, 90+)
  const overdueAmount = agingOverview.overdue_amount;
  const overduePercent =
    agingOverview.total_ap > 0
      ? (overdueAmount / agingOverview.total_ap) * 100
      : 0;

  // KPI Cards data
  const kpis: Array<{
    label: string;
    value: string;
    icon: React.ElementType;
    color: string;
    subtext?: string;
    trend?: number;
  }> = [
    {
      label: "Total AP",
      value: formatCurrency(agingOverview.total_ap || 0),
      icon: DollarSign,
      color: "blue",
      subtext: `Outstanding balance`,
    },
    {
      label: "Past Due",
      value: formatCurrency(overdueAmount || 0),
      icon: AlertTriangle,
      color: "red",
      subtext: `${overduePercent?.toFixed(1) || 0}% of total`,
    },
    {
      label: "Days Payable Outstanding",
      value: `${agingOverview.current_dpo?.toFixed(1) || 0} days`,
      icon: Calendar,
      color: "purple",
    },
    {
      label: "On-Time Payment Rate",
      value: `${agingOverview.on_time_rate?.toFixed(1) || 0}%`,
      icon: Percent,
      color: "green",
      subtext: "Last 90 days",
    },
  ];

  // Aging bucket colors
  const agingColors: Record<string, string> = {
    Current: "#10b981",
    "1-30 Days": "#3b82f6",
    "31-60 Days": "#f59e0b",
    "61-90 Days": "#f97316",
    "90+ Days": "#ef4444",
  };

  // Prepare aging bucket chart data
  const agingBucketData =
    agingOverview.buckets?.map((bucket) => ({
      name: bucket.bucket,
      amount: bucket.amount,
      count: bucket.count,
      percent: bucket.percentage,
      color: agingColors[bucket.bucket] || "#6b7280",
    })) || [];

  // Prepare supplier aging data
  const supplierAgingData =
    agingBySupplier?.slice(0, 10).map((sup) => ({
      name:
        sup.supplier.length > 20
          ? sup.supplier.substring(0, 20) + "..."
          : sup.supplier,
      fullName: sup.supplier,
      current: sup.current,
      overdue: sup.days_31_60 + sup.days_61_90 + sup.days_90_plus,
      total: sup.total_ap,
      daysOverdue: sup.avg_days_outstanding,
    })) || [];

  // Prepare DPO trend data
  const dpoTrendData =
    dpoTrends?.map((trend) => ({
      month: trend.month,
      dpo: trend.dpo,
      target: 45, // Target DPO
    })) || [];

  // Prepare cash flow forecast data
  const cashFlowData =
    cashForecast?.weeks?.map((week) => ({
      week: week.week,
      projected: week.amount_due,
      cumulative: week.amount_due, // Individual week amount
    })) || [];

  // Prepare payment terms compliance data
  const termsComplianceData =
    paymentTerms?.by_terms?.map((term) => ({
      name: term.terms,
      onTime: term.on_time_rate,
      late: 100 - term.on_time_rate,
      count: term.count,
      discountCaptured: 0,
    })) || [];

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <Clock className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Invoice Aging & Accounts Payable
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            AP aging analysis, DPO tracking, and cash flow management
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card
              key={kpi.label}
              className={cn(
                "border-l-4",
                kpi.color === "blue" && "border-l-blue-500",
                kpi.color === "red" && "border-l-red-500",
                kpi.color === "purple" && "border-l-purple-500",
                kpi.color === "green" && "border-l-green-500",
              )}
            >
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-2">
                  <Icon
                    className={cn(
                      "h-5 w-5",
                      kpi.color === "blue" && "text-blue-600",
                      kpi.color === "red" && "text-red-600",
                      kpi.color === "purple" && "text-purple-600",
                      kpi.color === "green" && "text-green-600",
                    )}
                  />
                  {kpi.trend !== undefined &&
                    (kpi.trend > 0 ? (
                      <TrendingUp className="h-4 w-4 text-red-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-green-500" />
                    ))}
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {kpi.value}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {kpi.label}
                </div>
                {kpi.subtext && (
                  <div className="text-xs text-gray-500 mt-1">
                    {kpi.subtext}
                  </div>
                )}
                {kpi.trend !== undefined && (
                  <div
                    className={cn(
                      "text-xs mt-1",
                      kpi.trend > 0 ? "text-red-600" : "text-green-600",
                    )}
                  >
                    {kpi.trend > 0 ? "+" : ""}
                    {kpi.trend.toFixed(1)} days vs last month
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Aging Buckets Chart */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Aging Bucket Analysis</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Outstanding AP by aging period
          </p>
        </CardHeader>
        <CardContent>
          {agingBucketData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={agingBucketData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                />
                <Tooltip content={<AgingBucketTooltip />} />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {agingBucketData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[350px] flex items-center justify-center text-gray-500">
              No aging data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* DPO Trends & Cash Flow Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DPO Trends */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>DPO Trend (12 Months)</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Days Payable Outstanding vs target
            </p>
          </CardHeader>
          <CardContent>
            {dpoTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={dpoTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                    domain={[0, "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                    formatter={(value: number, name: string) => [
                      `${value.toFixed(1)} days`,
                      name === "dpo" ? "Actual DPO" : "Target",
                    ]}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="dpo"
                    name="Actual DPO"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{ fill: "#3b82f6", r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="target"
                    name="Target"
                    stroke="#ef4444"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No DPO trend data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cash Flow Forecast */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-green-600" />
              <CardTitle>Cash Flow Forecast</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Projected payments over next 8 weeks
            </p>
          </CardHeader>
          <CardContent>
            {cashFlowData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={cashFlowData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="week"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                    formatter={(value: number, name: string) => [
                      formatCurrency(value),
                      name === "projected" ? "Weekly Payments" : "Cumulative",
                    ]}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="projected"
                    name="Weekly Payments"
                    fill="#3b82f6"
                    fillOpacity={0.3}
                    stroke="#3b82f6"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="cumulative"
                    name="Cumulative"
                    fill="#10b981"
                    fillOpacity={0.2}
                    stroke="#10b981"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No forecast data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Payment Terms Compliance */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Payment Terms Compliance</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            On-time payment rates by payment term
          </p>
        </CardHeader>
        <CardContent>
          {termsComplianceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={termsComplianceData}
                layout="vertical"
                margin={{ left: 80 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                  width={70}
                />
                <Tooltip content={<PaymentTermsTooltip />} />
                <Legend />
                <Bar
                  dataKey="onTime"
                  name="On Time %"
                  stackId="a"
                  fill="#10b981"
                  radius={[0, 0, 0, 0]}
                />
                <Bar
                  dataKey="late"
                  name="Late %"
                  stackId="a"
                  fill="#ef4444"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No payment terms data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Aged Suppliers */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-orange-600" />
            <CardTitle>Top Aged Suppliers</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Suppliers with highest overdue balances
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Supplier
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Current
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Overdue
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Total AP
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Avg Days Overdue
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {supplierAgingData.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-gray-500">
                      No supplier aging data available
                    </td>
                  </tr>
                ) : (
                  supplierAgingData.map((supplier, index) => (
                    <tr
                      key={index}
                      className={cn(
                        "border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors",
                        supplier.daysOverdue > 60 &&
                          "bg-red-50 dark:bg-red-900/10",
                      )}
                    >
                      <td className="py-3 px-4">
                        <div
                          className="font-medium text-gray-900 dark:text-gray-100"
                          title={supplier.fullName}
                        >
                          {supplier.name}
                        </div>
                      </td>
                      <td className="text-right py-3 px-4 font-mono text-green-600">
                        {formatCurrency(supplier.current)}
                      </td>
                      <td className="text-right py-3 px-4 font-mono text-red-600">
                        {formatCurrency(supplier.overdue)}
                      </td>
                      <td className="text-right py-3 px-4 font-mono font-semibold">
                        {formatCurrency(supplier.total)}
                      </td>
                      <td className="text-center py-3 px-4 font-mono">
                        {supplier.daysOverdue?.toFixed(0) || "-"}
                      </td>
                      <td className="text-center py-3 px-4">
                        {supplier.daysOverdue > 90 ? (
                          <Badge variant="destructive">Critical</Badge>
                        ) : supplier.daysOverdue > 60 ? (
                          <Badge className="bg-orange-500">Warning</Badge>
                        ) : supplier.daysOverdue > 30 ? (
                          <Badge variant="secondary">Monitor</Badge>
                        ) : (
                          <Badge className="bg-green-500">Good</Badge>
                        )}
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
