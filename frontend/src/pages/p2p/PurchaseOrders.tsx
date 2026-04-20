import { useState } from "react";
import {
  usePOOverview,
  usePOLeakage,
  usePOAmendments,
  usePOBySupplier,
  usePODetail,
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
import { type TooltipProps } from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  ShoppingCart,
  DollarSign,
  FileCheck,
  AlertTriangle,
  Building2,
  TrendingUp,
  Edit3,
  Loader2,
  Eye,
  FileText,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import type { POLeakageCategory } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

// Custom tooltip type definitions
interface ContractCoverageData {
  name: string;
  value: number;
  color: string;
}

interface LeakageChartData {
  name: string;
  fullName: string;
  maverickValue: number;
  maverickPercent: number;
  totalValue: number;
}

interface AmendmentChartData {
  name: string;
  count: number;
  avgChange: number;
  totalChange: number;
}

// Custom tooltip for Contract Coverage Pie Chart
const ContractCoverageTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as ContractCoverageData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Value: {formatCurrency(data.value)}
      </div>
    </div>
  );
};

// Custom tooltip for Leakage Bar Chart
const LeakageTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as LeakageChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Maverick: {formatCurrency(data.maverickValue)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        % of Category: {data.maverickPercent?.toFixed(1)}%
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Total Category: {formatCurrency(data.totalValue)}
      </div>
    </div>
  );
};

// Custom tooltip for Amendment Bar Chart
const AmendmentTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as AmendmentChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Count: {data.count.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Avg Change: {formatCurrency(data.avgChange)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Total Change: {formatCurrency(data.totalChange)}
      </div>
    </div>
  );
};

/**
 * Purchase Order Analysis - PO management, contract coverage, and amendment tracking
 * Shows PO volume, maverick spend, contract coverage, and change order patterns
 */
export default function PurchaseOrders() {
  const { data: poOverview, isLoading: overviewLoading } = usePOOverview();
  const { data: poLeakage, isLoading: leakageLoading } = usePOLeakage();
  const { data: poAmendments, isLoading: amendLoading } = usePOAmendments();
  const { data: poBySupplier, isLoading: supplierLoading } = usePOBySupplier();

  const [selectedPOId, setSelectedPOId] = useState<number | null>(null);
  const { data: poDetail, isLoading: detailLoading } =
    usePODetail(selectedPOId);

  const isLoading =
    overviewLoading || leakageLoading || amendLoading || supplierLoading;

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart height={300} type="pie" />
          <SkeletonChart height={300} type="bar" />
        </div>
      </div>
    );
  }

  // No data state
  if (!poOverview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <ShoppingCart className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No PO Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload purchase order data to see analysis.
          </p>
        </div>
      </div>
    );
  }

  // KPI Cards data
  const kpis = [
    {
      label: "Total POs",
      value: poOverview.total_count?.toLocaleString() || "0",
      icon: ShoppingCart,
      color: "blue",
      subtext: `${formatCurrency(poOverview.total_value || 0)} committed`,
    },
    {
      label: "Contract Coverage",
      value: `${poOverview.contract_coverage_pct?.toFixed(1) || 0}%`,
      icon: FileCheck,
      color: "green",
      subtext: "On-contract spend",
    },
    {
      label: "Maverick Spend",
      value: formatCurrency(poOverview.off_contract_value || 0),
      icon: AlertTriangle,
      color: "red",
      subtext: `Off-contract POs`,
    },
    {
      label: "Amendment Rate",
      value: `${poOverview.amendment_rate?.toFixed(1) || 0}%`,
      icon: Edit3,
      color: "orange",
      subtext: `POs with changes`,
    },
  ];

  // Contract coverage pie chart
  const contractCoverageData = [
    {
      name: "On Contract",
      value: poOverview.on_contract_value || 0,
      color: "#10b981",
    },
    {
      name: "Off Contract",
      value: poOverview.off_contract_value || 0,
      color: "#ef4444",
    },
  ];

  // PO Leakage by category data
  const leakageCategories =
    poLeakage && "by_category" in poLeakage
      ? poLeakage.by_category
      : Array.isArray(poLeakage)
        ? poLeakage
        : [];
  const leakageData =
    leakageCategories?.slice(0, 8).map((cat: POLeakageCategory) => ({
      name:
        cat.category.length > 20
          ? cat.category.substring(0, 20) + "..."
          : cat.category,
      fullName: cat.category,
      maverickValue: cat.off_contract_value,
      maverickPercent: cat.off_contract_pct,
      totalValue: cat.total_value,
    })) || [];

  // Amendment analysis data
  const amendmentData =
    poAmendments?.by_reason?.map((reason) => ({
      name: reason.reason,
      count: reason.count,
      avgChange: reason.avg_change,
      totalChange: reason.total_change,
    })) || [];

  // Supplier PO data
  const supplierPOData =
    poBySupplier?.slice(0, 10).map((sup) => ({
      name:
        sup.supplier.length > 20
          ? sup.supplier.substring(0, 20) + "..."
          : sup.supplier,
      fullName: sup.supplier,
      poCount: sup.po_count,
      totalValue: sup.total_value,
      avgValue: sup.total_value / (sup.po_count || 1),
      contractCoverage: sup.on_contract_pct,
    })) || [];

  // PO status badge
  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: "bg-gray-100 text-gray-800",
      pending_approval: "bg-yellow-100 text-yellow-800",
      approved: "bg-blue-100 text-blue-800",
      sent_to_supplier: "bg-purple-100 text-purple-800",
      acknowledged: "bg-indigo-100 text-indigo-800",
      partially_received: "bg-orange-100 text-orange-800",
      fully_received: "bg-green-100 text-green-800",
      closed: "bg-gray-100 text-gray-800",
      cancelled: "bg-red-100 text-red-800",
    };
    return styles[status] || styles.draft;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <ShoppingCart className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Purchase Order Analysis
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            PO management, contract coverage, and amendment tracking
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
                kpi.color === "red" && "border-l-red-500",
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
                      kpi.color === "red" && "text-red-600",
                      kpi.color === "orange" && "text-orange-600",
                    )}
                  />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {kpi.value}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {kpi.label}
                </div>
                <div className="text-xs text-gray-500 mt-1">{kpi.subtext}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contract Coverage Pie */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-green-600" />
              <CardTitle>Contract Coverage Analysis</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              PO value by contract status
            </p>
          </CardHeader>
          <CardContent>
            {contractCoverageData.some((d) => d.value > 0) ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={contractCoverageData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) =>
                      `${name}: ${(percent * 100).toFixed(1)}%`
                    }
                  >
                    {contractCoverageData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ContractCoverageTooltip />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No contract coverage data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* PO Leakage by Category */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <CardTitle>PO Leakage by Category</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Off-contract spend by category
            </p>
          </CardHeader>
          <CardContent>
            {leakageData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={leakageData}
                  layout="vertical"
                  margin={{ left: 100 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                  />
                  <YAxis
                    dataKey="name"
                    type="category"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                    width={90}
                  />
                  <Tooltip content={<LeakageTooltip />} />
                  <Bar
                    dataKey="maverickValue"
                    fill="#ef4444"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No leakage data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Amendment Analysis */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Edit3 className="h-5 w-5 text-orange-600" />
            <CardTitle>Amendment Analysis</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            PO change order patterns and reasons
          </p>
        </CardHeader>
        <CardContent>
          {amendmentData.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={amendmentData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                    angle={-30}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tick={{ fontSize: 11 }} stroke="#6b7280" />
                  <Tooltip content={<AmendmentTooltip />} />
                  <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <div className="space-y-4">
                <h4 className="font-semibold text-gray-900 dark:text-gray-100">
                  Key Metrics
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                    <div className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                      {poAmendments?.total_amended?.toLocaleString() || "0"}
                    </div>
                    <div className="text-sm text-orange-700 dark:text-orange-300">
                      Amended POs
                    </div>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                    <div className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                      {formatCurrency(poAmendments?.total_value_change || 0)}
                    </div>
                    <div className="text-sm text-orange-700 dark:text-orange-300">
                      Total Value Change
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    <strong>Impact:</strong>{" "}
                    {poAmendments?.amendment_rate?.toFixed(1) || 0}% of POs had
                    amendments with average change of{" "}
                    {formatCurrency(poAmendments?.avg_value_change || 0)}.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No amendment data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Suppliers by PO Volume */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600" />
            <CardTitle>POs by Supplier</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Top suppliers by PO count and value
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
                    PO Count
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Total Value
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Avg PO Value
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Contract Coverage
                  </th>
                </tr>
              </thead>
              <tbody>
                {supplierPOData.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-gray-500">
                      No supplier data available
                    </td>
                  </tr>
                ) : (
                  supplierPOData.map((supplier, index) => (
                    <tr
                      key={index}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div
                          className="font-medium text-gray-900 dark:text-gray-100"
                          title={supplier.fullName}
                        >
                          {supplier.name}
                        </div>
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {supplier.poCount?.toLocaleString()}
                      </td>
                      <td className="text-right py-3 px-4 font-mono font-semibold">
                        {formatCurrency(supplier.totalValue)}
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {formatCurrency(supplier.avgValue)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Progress
                            value={supplier.contractCoverage || 0}
                            className="h-2 flex-1"
                          />
                          <span className="text-sm font-mono w-12 text-right">
                            {supplier.contractCoverage?.toFixed(0) || 0}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* PO Detail Modal */}
      <Dialog open={!!selectedPOId} onOpenChange={() => setSelectedPOId(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5 text-blue-600" />
              Purchase Order Detail
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : poDetail ? (
            <div className="space-y-6">
              {/* Header Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    PO Number
                  </label>
                  <p className="font-mono text-lg">{poDetail.po_number}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Status
                  </label>
                  <div className="mt-1">
                    <Badge className={getStatusBadge(poDetail.status)}>
                      {poDetail.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Supplier
                  </label>
                  <p className="text-lg">{poDetail.supplier_name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Total Amount
                  </label>
                  <p className="text-lg font-semibold">
                    {formatCurrency(poDetail.total_amount)}
                  </p>
                </div>
              </div>

              {/* Contract Info */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold mb-3">Contract Information</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Contract Backed</div>
                    <div className="font-medium">
                      {poDetail.is_contract_backed ? (
                        <Badge className="bg-green-100 text-green-800">
                          Yes
                        </Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-800">
                          No (Maverick)
                        </Badge>
                      )}
                    </div>
                  </div>
                  {poDetail.contract_number && (
                    <div>
                      <div className="text-gray-500">Contract #</div>
                      <div className="font-medium">
                        {poDetail.contract_number}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Dates */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold mb-3">Timeline</h4>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Created</div>
                    <div className="font-medium">
                      {poDetail.created_date || "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Approved</div>
                    <div className="font-medium">
                      {poDetail.approval_date || "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Required</div>
                    <div className="font-medium">
                      {poDetail.required_date || "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Promised</div>
                    <div className="font-medium">
                      {poDetail.promised_date || "-"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Amendment History */}
              {poDetail.amendment_count > 0 && (
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Edit3 className="h-5 w-5 text-orange-600" />
                    <h4 className="font-semibold text-orange-900 dark:text-orange-100">
                      Amendments
                    </h4>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-orange-700 dark:text-orange-300">
                        Amendment Count
                      </div>
                      <div className="font-semibold text-orange-900 dark:text-orange-100">
                        {poDetail.amendment_count}
                      </div>
                    </div>
                    <div>
                      <div className="text-orange-700 dark:text-orange-300">
                        Original Amount
                      </div>
                      <div className="font-semibold text-orange-900 dark:text-orange-100">
                        {formatCurrency(
                          poDetail.original_amount || poDetail.total_amount,
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="text-orange-700 dark:text-orange-300">
                        Change
                      </div>
                      <div className="font-semibold text-orange-900 dark:text-orange-100">
                        {formatCurrency(
                          (poDetail.total_amount || 0) -
                            (poDetail.original_amount ||
                              poDetail.total_amount ||
                              0),
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Linked PRs */}
              {poDetail.linked_prs && poDetail.linked_prs.length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Linked Requisitions
                  </label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {poDetail.linked_prs.map((pr) => (
                      <Badge
                        key={pr.id}
                        variant="outline"
                        className="font-mono"
                      >
                        {pr.pr_number}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              PO detail not found
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
