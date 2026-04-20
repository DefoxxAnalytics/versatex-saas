import { useState } from "react";
import {
  useSupplierPaymentsOverview,
  useSupplierPaymentsScorecard,
  useSupplierPaymentDetail,
  useSupplierPaymentHistory,
} from "@/hooks/useP2PAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  BarChart,
  Bar,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { type TooltipProps } from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  CreditCard,
  Building2,
  Clock,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  Percent,
  Loader2,
  Eye,
  Star,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import type {
  SupplierPaymentScore,
  SupplierPaymentHistoryItem,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

// Custom tooltip type definitions
interface SupplierDPOChartData {
  name: string;
  fullName: string;
  supplierId: number;
  apBalance: number;
  dpo: number;
  onTimeRate: number;
  exceptionRate: number;
  score: number;
}

interface PaymentHistoryChartData {
  date: string;
  amount: number;
  daysToPayment: number;
  onTime: boolean;
}

// Custom tooltip for DPO Comparison Chart
const SupplierDPOTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as SupplierDPOChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        DPO: {data.dpo?.toFixed(0)} days
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        AP Balance: {formatCurrency(data.apBalance)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        On-Time: {data.onTimeRate?.toFixed(1)}%
      </div>
    </div>
  );
};

// Custom tooltip for Payment History Chart
const PaymentHistoryTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as PaymentHistoryChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.date}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Payment Amount: {formatCurrency(data.amount)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Days to Payment: {data.daysToPayment}
      </div>
    </div>
  );
};

/**
 * Supplier Payment Performance - Supplier-centric view of payment and P2P metrics
 * Shows payment scorecards, DPO by supplier, exception rates, and payment history
 */
export default function SupplierPayments() {
  const { data: overview, isLoading: overviewLoading } =
    useSupplierPaymentsOverview();
  const { data: scorecard, isLoading: scorecardLoading } =
    useSupplierPaymentsScorecard();

  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(
    null,
  );
  const { data: supplierDetail, isLoading: detailLoading } =
    useSupplierPaymentDetail(selectedSupplierId);
  const { data: paymentHistory, isLoading: historyLoading } =
    useSupplierPaymentHistory(selectedSupplierId);

  const isLoading = overviewLoading || scorecardLoading;

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonChart height={400} type="bar" />
      </div>
    );
  }

  // No data state
  if (!overview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <CreditCard className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No Payment Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload supplier payment data to see performance analysis.
          </p>
        </div>
      </div>
    );
  }

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
      label: "Active Suppliers",
      value: overview.total_suppliers?.toLocaleString() || "0",
      icon: Building2,
      color: "blue",
      subtext: "With AP balance",
    },
    {
      label: "On-Time Payment Rate",
      value: `${overview.avg_on_time_rate?.toFixed(1) || 0}%`,
      icon: CheckCircle2,
      color: "green",
      subtext: "Last 90 days",
    },
    {
      label: "Avg Supplier DPO",
      value: `${overview.avg_dpo?.toFixed(1) || 0} days`,
      icon: Clock,
      color: "purple",
    },
    {
      label: "Exception Rate",
      value: `${overview.avg_exception_rate?.toFixed(1) || 0}%`,
      icon: AlertTriangle,
      color: "orange",
      subtext: "Invoices with issues",
    },
  ];

  // Supplier scorecard data
  const scorecardData =
    scorecard?.suppliers?.map((sup: SupplierPaymentScore) => ({
      name:
        sup.supplier.length > 25
          ? sup.supplier.substring(0, 25) + "..."
          : sup.supplier,
      fullName: sup.supplier,
      supplierId: sup.supplier_id,
      apBalance: sup.total_ap,
      dpo: sup.avg_dpo,
      onTimeRate: sup.on_time_rate,
      exceptionRate: sup.exception_rate,
      score: sup.performance_score,
    })) || [];

  // Get score badge color
  const getScoreBadge = (score: number) => {
    if (score >= 80)
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
    if (score >= 60)
      return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300";
    if (score >= 40)
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300";
    return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
  };

  // Get score label
  const getScoreLabel = (score: number) => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Poor";
  };

  // Payment history chart data - paymentHistory can be object with recent_invoices or an array
  const recentInvoices =
    paymentHistory && "recent_invoices" in paymentHistory
      ? paymentHistory.recent_invoices
      : Array.isArray(paymentHistory)
        ? paymentHistory
        : [];
  const historyChartData =
    recentInvoices?.slice(0, 20).map((payment: SupplierPaymentHistoryItem) => ({
      date: payment.paid_date,
      amount: payment.invoice_amount || payment.amount,
      daysToPayment: payment.days_to_pay,
      onTime: payment.on_time,
    })) || [];

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <CreditCard className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Supplier Payment Performance
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Supplier-centric view of payment metrics and scorecards
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
                kpi.color === "green" && "border-l-green-500",
                kpi.color === "purple" && "border-l-purple-500",
                kpi.color === "orange" && "border-l-orange-500",
              )}
            >
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-2">
                  <Icon
                    className={cn(
                      "h-5 w-5",
                      kpi.color === "blue" && "text-blue-600",
                      kpi.color === "green" && "text-green-600",
                      kpi.color === "purple" && "text-purple-600",
                      kpi.color === "orange" && "text-orange-600",
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

      {/* Supplier Scorecard Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-500" />
            <CardTitle>Supplier Payment Scorecard</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Performance scores based on payment behavior
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
                    AP Balance
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    DPO
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    On-Time %
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Exception %
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Score
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {scorecardData.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">
                      No supplier scorecard data available
                    </td>
                  </tr>
                ) : (
                  scorecardData.map((supplier) => (
                    <tr
                      key={supplier.supplierId}
                      className={cn(
                        "border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer",
                        (supplier.score ?? 0) < 40 &&
                          "bg-red-50 dark:bg-red-900/10",
                      )}
                      onClick={() => setSelectedSupplierId(supplier.supplierId)}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className={cn(
                              "w-2 h-2 rounded-full",
                              (supplier.score ?? 0) >= 80
                                ? "bg-green-500"
                                : (supplier.score ?? 0) >= 60
                                  ? "bg-blue-500"
                                  : (supplier.score ?? 0) >= 40
                                    ? "bg-yellow-500"
                                    : "bg-red-500",
                            )}
                          />
                          <span
                            className="font-medium text-gray-900 dark:text-gray-100"
                            title={supplier.fullName}
                          >
                            {supplier.name}
                          </span>
                        </div>
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {formatCurrency(supplier.apBalance ?? 0)}
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {supplier.dpo?.toFixed(0) || "-"} days
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <Progress
                            value={supplier.onTimeRate || 0}
                            className={cn(
                              "h-2 w-16",
                              supplier.onTimeRate >= 80
                                ? "[&>div]:bg-green-500"
                                : supplier.onTimeRate >= 60
                                  ? "[&>div]:bg-blue-500"
                                  : "[&>div]:bg-red-500",
                            )}
                          />
                          <span className="text-sm font-mono w-10 text-right">
                            {supplier.onTimeRate?.toFixed(0) || 0}%
                          </span>
                        </div>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Badge
                          variant={
                            supplier.exceptionRate > 15
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {supplier.exceptionRate?.toFixed(1) || 0}%
                        </Badge>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Badge className={getScoreBadge(supplier.score || 0)}>
                          {supplier.score?.toFixed(0) || "-"} -{" "}
                          {getScoreLabel(supplier.score || 0)}
                        </Badge>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedSupplierId(supplier.supplierId);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* DPO Comparison Chart */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>DPO Comparison by Supplier</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Days Payable Outstanding for top suppliers
          </p>
        </CardHeader>
        <CardContent>
          {scorecardData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart
                data={scorecardData.slice(0, 15)}
                layout="vertical"
                margin={{ left: 150 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" tick={{ fontSize: 11 }} stroke="#6b7280" />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                  width={140}
                />
                <Tooltip content={<SupplierDPOTooltip />} />
                <Bar dataKey="dpo" fill="#8b5cf6" radius={[0, 4, 4, 0]}>
                  {scorecardData.slice(0, 15).map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        (entry.dpo ?? 0) > 60
                          ? "#ef4444"
                          : (entry.dpo ?? 0) > 45
                            ? "#f59e0b"
                            : "#8b5cf6"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[350px] flex items-center justify-center text-gray-500">
              No DPO data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Supplier Detail Modal */}
      <Dialog
        open={!!selectedSupplierId}
        onOpenChange={() => setSelectedSupplierId(null)}
      >
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600" />
              Supplier Payment Detail
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : supplierDetail ? (
            <div className="space-y-6">
              {/* Supplier Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    {supplierDetail.supplier}
                  </h3>
                  <p className="text-sm text-gray-500">
                    Supplier ID: {supplierDetail.supplier_id}
                  </p>
                </div>
                <Badge
                  className={getScoreBadge(
                    supplierDetail.performance_score || 0,
                  )}
                >
                  Score: {supplierDetail.performance_score?.toFixed(0) || "-"} -{" "}
                  {getScoreLabel(supplierDetail.performance_score || 0)}
                </Badge>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <DollarSign className="h-5 w-5 text-blue-600 mb-2" />
                  <div className="text-xl font-bold text-blue-900 dark:text-blue-100">
                    {formatCurrency(supplierDetail.total_ap || 0)}
                  </div>
                  <div className="text-sm text-blue-700 dark:text-blue-300">
                    AP Balance
                  </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <Clock className="h-5 w-5 text-purple-600 mb-2" />
                  <div className="text-xl font-bold text-purple-900 dark:text-purple-100">
                    {supplierDetail.avg_dpo?.toFixed(0) || "-"} days
                  </div>
                  <div className="text-sm text-purple-700 dark:text-purple-300">
                    Avg DPO
                  </div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <Percent className="h-5 w-5 text-green-600 mb-2" />
                  <div className="text-xl font-bold text-green-900 dark:text-green-100">
                    {supplierDetail.on_time_rate?.toFixed(1) || 0}%
                  </div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    On-Time Rate
                  </div>
                </div>
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                  <AlertTriangle className="h-5 w-5 text-orange-600 mb-2" />
                  <div className="text-xl font-bold text-orange-900 dark:text-orange-100">
                    {supplierDetail.exception_rate?.toFixed(1) || 0}%
                  </div>
                  <div className="text-sm text-orange-700 dark:text-orange-300">
                    Exception Rate
                  </div>
                </div>
              </div>

              {/* Invoice Stats */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold mb-3">Invoice Statistics</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Total Invoices</div>
                    <div className="font-semibold">
                      {supplierDetail.invoice_count?.toLocaleString() || 0}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Avg Invoice Value</div>
                    <div className="font-semibold">
                      {formatCurrency(
                        (supplierDetail.total_ap || 0) /
                          (supplierDetail.invoice_count || 1),
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Payment Performance</div>
                    <div className="font-semibold">
                      {getScoreLabel(supplierDetail.performance_score || 0)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Payment History Chart */}
              {historyLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                </div>
              ) : historyChartData.length > 0 ? (
                <div>
                  <h4 className="font-semibold mb-3">
                    Payment History (Last 20 Payments)
                  </h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={historyChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10 }}
                        stroke="#6b7280"
                      />
                      <YAxis
                        yAxisId="left"
                        tick={{ fontSize: 11 }}
                        stroke="#6b7280"
                        tickFormatter={(value) =>
                          `$${(value / 1000).toFixed(0)}K`
                        }
                      />
                      <YAxis
                        yAxisId="right"
                        orientation="right"
                        tick={{ fontSize: 11 }}
                        stroke="#6b7280"
                      />
                      <Tooltip content={<PaymentHistoryTooltip />} />
                      <Legend />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="amount"
                        name="Payment Amount"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ fill: "#3b82f6", r: 3 }}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="daysToPayment"
                        name="Days to Payment"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        dot={{ fill: "#f59e0b", r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No payment history available
                </div>
              )}

              {/* Recent Payments Table */}
              {recentInvoices && recentInvoices.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-3">Recent Payments</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-gray-700">
                          <th className="text-left py-2 px-3 font-semibold">
                            Invoice #
                          </th>
                          <th className="text-left py-2 px-3 font-semibold">
                            Payment Date
                          </th>
                          <th className="text-right py-2 px-3 font-semibold">
                            Amount
                          </th>
                          <th className="text-center py-2 px-3 font-semibold">
                            Days to Pay
                          </th>
                          <th className="text-center py-2 px-3 font-semibold">
                            Status
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentInvoices
                          .slice(0, 10)
                          .map(
                            (
                              payment: SupplierPaymentHistoryItem,
                              idx: number,
                            ) => (
                              <tr
                                key={idx}
                                className="border-b border-gray-100 dark:border-gray-800"
                              >
                                <td className="py-2 px-3 font-mono">
                                  {payment.invoice_number}
                                </td>
                                <td className="py-2 px-3">
                                  {payment.paid_date}
                                </td>
                                <td className="text-right py-2 px-3 font-mono">
                                  {formatCurrency(
                                    payment.invoice_amount ||
                                      payment.amount ||
                                      0,
                                  )}
                                </td>
                                <td className="text-center py-2 px-3 font-mono">
                                  {payment.days_to_pay}
                                </td>
                                <td className="text-center py-2 px-3">
                                  {payment.on_time ? (
                                    <Badge className="bg-green-100 text-green-800">
                                      On Time
                                    </Badge>
                                  ) : (
                                    <Badge className="bg-red-100 text-red-800">
                                      Late
                                    </Badge>
                                  )}
                                </td>
                              </tr>
                            ),
                          )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Supplier detail not found
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
