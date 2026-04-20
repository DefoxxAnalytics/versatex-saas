import { useState } from "react";
import {
  useP2PCycleOverview,
  useP2PCycleByCategory,
  useP2PCycleBySupplier,
  useP2PCycleTrends,
  useP2PBottlenecks,
  useP2PProcessFunnel,
  useP2PStageDrilldown,
} from "@/hooks/useP2PAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  FunnelChart,
  Funnel,
  LabelList,
  type TooltipProps,
} from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  ArrowRightLeft,
  Clock,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  Loader2,
  FileText,
  Package,
  Receipt,
  CreditCard,
  ArrowRight,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import { cn } from "@/lib/utils";

// Custom tooltip for category chart
interface CategoryChartData {
  name: string;
  fullName: string;
  avgDays: number;
  prCount: number;
  totalSpend: number;
}

const CategoryChartTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as CategoryChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Avg Cycle: {data.avgDays.toFixed(1)} days
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        PRs: {data.prCount.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Spend: {formatCurrency(data.totalSpend)}
      </div>
    </div>
  );
};

// Custom tooltip for supplier chart
interface SupplierChartData {
  name: string;
  fullName: string;
  avgDays: number;
  poCount: number;
  totalSpend: number;
}

const SupplierChartTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as SupplierChartData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Avg Cycle: {data.avgDays.toFixed(1)} days
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        POs: {data.poCount.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Spend: {formatCurrency(data.totalSpend)}
      </div>
    </div>
  );
};

/**
 * P2P Cycle Dashboard - End-to-end process visibility and cycle time analysis
 * Shows PR → PO → GR → Invoice → Payment cycle times and bottlenecks
 */
export default function P2PCycle() {
  const { data: cycleOverview, isLoading: overviewLoading } =
    useP2PCycleOverview();
  const { data: cycleByCategory, isLoading: categoryLoading } =
    useP2PCycleByCategory();
  const { data: cycleBySupplier, isLoading: supplierLoading } =
    useP2PCycleBySupplier();
  const { data: cycleTrends, isLoading: trendsLoading } = useP2PCycleTrends(12);
  const { data: bottlenecks, isLoading: bottlenecksLoading } =
    useP2PBottlenecks();
  const { data: processFunnel, isLoading: funnelLoading } =
    useP2PProcessFunnel();

  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const { data: stageDrilldown, isLoading: drilldownLoading } =
    useP2PStageDrilldown(selectedStage);

  const isLoading =
    overviewLoading ||
    categoryLoading ||
    supplierLoading ||
    trendsLoading ||
    bottlenecksLoading ||
    funnelLoading;

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonChart height={350} type="bar" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart height={300} type="line" />
          <SkeletonChart height={300} type="bar" />
        </div>
      </div>
    );
  }

  // No data state
  if (!cycleOverview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <ArrowRightLeft className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No P2P Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload PR, PO, GR, and Invoice data to see cycle time analysis.
          </p>
        </div>
      </div>
    );
  }

  // Stage cycle time data for KPI cards
  const stages = [
    {
      label: "PR → PO",
      days: cycleOverview.stages.pr_to_po.avg_days,
      target: cycleOverview.stages.pr_to_po.target_days,
      icon: FileText,
      color: "blue",
      stage: "pr_to_po",
      status: cycleOverview.stages.pr_to_po.status,
    },
    {
      label: "PO → GR",
      days: cycleOverview.stages.po_to_gr.avg_days,
      target: cycleOverview.stages.po_to_gr.target_days,
      icon: Package,
      color: "purple",
      stage: "po_to_gr",
      status: cycleOverview.stages.po_to_gr.status,
    },
    {
      label: "GR → Invoice",
      days: cycleOverview.stages.gr_to_invoice.avg_days,
      target: cycleOverview.stages.gr_to_invoice.target_days,
      icon: Receipt,
      color: "orange",
      stage: "gr_to_invoice",
      status: cycleOverview.stages.gr_to_invoice.status,
    },
    {
      label: "Invoice → Pay",
      days: cycleOverview.stages.invoice_to_payment.avg_days,
      target: cycleOverview.stages.invoice_to_payment.target_days,
      icon: CreditCard,
      color: "green",
      stage: "invoice_to_payment",
      status: cycleOverview.stages.invoice_to_payment.status,
    },
    {
      label: "Total Cycle",
      days: cycleOverview.total_cycle.avg_days,
      target: cycleOverview.total_cycle.target_days,
      icon: Clock,
      color: "indigo",
      stage: "total",
      status: "on_track" as const,
    },
  ];

  // Get status color based on variance from target
  const getStatusColor = (actual: number, target: number) => {
    const variance = ((actual - target) / target) * 100;
    if (variance <= 0)
      return "text-green-600 bg-green-100 dark:bg-green-900/30";
    if (variance <= 25)
      return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30";
    return "text-red-600 bg-red-100 dark:bg-red-900/30";
  };

  // Get trend icon
  const getTrendIcon = (actual: number, target: number) => {
    if (actual <= target)
      return <TrendingDown className="h-4 w-4 text-green-600" />;
    return <TrendingUp className="h-4 w-4 text-red-600" />;
  };

  // Prepare funnel chart data
  const funnelData =
    processFunnel?.stages?.map((stage) => ({
      name: stage.stage,
      value: stage.count,
      fill: "#3b82f6",
    })) || [];

  // Prepare trend chart data
  const trendChartData =
    cycleTrends?.map((trend) => ({
      month: trend.month,
      prToPo: trend.pr_to_po_days,
      poToGr: trend.po_to_gr_days,
      grToInv: trend.gr_to_invoice_days,
      invToPay: trend.invoice_to_payment_days,
      total: trend.total_days,
    })) || [];

  // Prepare category comparison data
  const categoryChartData =
    cycleByCategory?.slice(0, 10).map((cat) => ({
      name:
        cat.category.length > 20
          ? cat.category.substring(0, 20) + "..."
          : cat.category,
      fullName: cat.category,
      avgDays: cat.total_days,
      prCount: cat.transaction_count,
      totalSpend: cat.total_spend,
    })) || [];

  // Prepare supplier comparison data
  const supplierChartData =
    cycleBySupplier?.slice(0, 10).map((sup) => ({
      name:
        sup.supplier.length > 15
          ? sup.supplier.substring(0, 15) + "..."
          : sup.supplier,
      fullName: sup.supplier,
      avgDays: sup.total_days,
      poCount: sup.transaction_count,
      totalSpend: sup.on_time_rate,
    })) || [];

  // Bottleneck status badge
  const getBottleneckBadge = (variance: number) => {
    if (variance > 100) return <Badge variant="destructive">Critical</Badge>;
    if (variance > 50) return <Badge className="bg-orange-500">Warning</Badge>;
    if (variance > 0) return <Badge variant="secondary">Monitor</Badge>;
    return <Badge className="bg-green-500">On Track</Badge>;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <ArrowRightLeft className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            P2P Cycle Analysis
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            End-to-end procure-to-pay cycle time visibility
          </p>
        </div>
      </div>

      {/* Stage KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stages.map((stage) => {
          const Icon = stage.icon;
          const variance =
            stage.target > 0
              ? ((stage.days - stage.target) / stage.target) * 100
              : 0;

          return (
            <Card
              key={stage.stage}
              className={cn(
                "cursor-pointer transition-all hover:shadow-lg border-l-4",
                stage.color === "blue" && "border-l-blue-500",
                stage.color === "purple" && "border-l-purple-500",
                stage.color === "orange" && "border-l-orange-500",
                stage.color === "green" && "border-l-green-500",
                stage.color === "indigo" && "border-l-indigo-500",
              )}
              onClick={() => setSelectedStage(stage.stage)}
            >
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-2">
                  <Icon
                    className={cn(
                      "h-5 w-5",
                      stage.color === "blue" && "text-blue-600",
                      stage.color === "purple" && "text-purple-600",
                      stage.color === "orange" && "text-orange-600",
                      stage.color === "green" && "text-green-600",
                      stage.color === "indigo" && "text-indigo-600",
                    )}
                  />
                  {getTrendIcon(stage.days, stage.target)}
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {stage.days.toFixed(1)}{" "}
                  <span className="text-sm font-normal text-gray-500">
                    days
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {stage.label}
                </div>
                <div
                  className={cn(
                    "text-xs mt-2 px-2 py-1 rounded-full inline-block",
                    getStatusColor(stage.days, stage.target),
                  )}
                >
                  Target: {stage.target}d ({variance > 0 ? "+" : ""}
                  {variance.toFixed(0)}%)
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Process Funnel & Trends Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Process Funnel */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ArrowRight className="h-5 w-5 text-blue-600" />
              <CardTitle>Process Flow Funnel</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Document volume through each stage
            </p>
          </CardHeader>
          <CardContent>
            {funnelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <FunnelChart>
                  <Tooltip
                    formatter={(value: number) => [
                      value.toLocaleString(),
                      "Documents",
                    ]}
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                  />
                  <Funnel dataKey="value" data={funnelData} isAnimationActive>
                    <LabelList
                      position="right"
                      fill="#000"
                      stroke="none"
                      dataKey="name"
                    />
                  </Funnel>
                </FunnelChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No funnel data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cycle Time Trends */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-green-600" />
              <CardTitle>Cycle Time Trends</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Monthly average cycle times (12 months)
            </p>
          </CardHeader>
          <CardContent>
            {trendChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                    stroke="#6b7280"
                  />
                  <YAxis tick={{ fontSize: 11 }} stroke="#6b7280" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                    formatter={(value: number, name: string) => [
                      `${value.toFixed(1)} days`,
                      name === "total"
                        ? "Total Cycle"
                        : name === "prToPo"
                          ? "PR → PO"
                          : name === "poToGr"
                            ? "PO → GR"
                            : name === "grToInv"
                              ? "GR → Invoice"
                              : "Invoice → Pay",
                    ]}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke="#6366f1"
                    strokeWidth={3}
                  />
                  <Line
                    type="monotone"
                    dataKey="prToPo"
                    name="PR→PO"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                  <Line
                    type="monotone"
                    dataKey="poToGr"
                    name="PO→GR"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                  <Line
                    type="monotone"
                    dataKey="grToInv"
                    name="GR→Inv"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                  <Line
                    type="monotone"
                    dataKey="invToPay"
                    name="Inv→Pay"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No trend data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottleneck Analysis */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            <CardTitle>Bottleneck Analysis</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Identify where delays occur in the P2P process
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Stage
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Avg Days
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Target
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Variance
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Impact
                  </th>
                </tr>
              </thead>
              <tbody>
                {bottlenecks?.bottlenecks?.map((bottleneck, index) => (
                  <tr
                    key={bottleneck.stage}
                    className={cn(
                      "border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors",
                      index === 0 &&
                        bottleneck.variance_pct > 50 &&
                        "bg-red-50 dark:bg-red-900/10",
                    )}
                    onClick={() => setSelectedStage(bottleneck.stage)}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {bottleneck.stage}
                        </span>
                      </div>
                    </td>
                    <td className="text-right py-3 px-4 font-mono text-gray-900 dark:text-gray-100">
                      {bottleneck.avg_days.toFixed(1)}
                    </td>
                    <td className="text-right py-3 px-4 font-mono text-gray-500">
                      {bottleneck.target_days.toFixed(1)}
                    </td>
                    <td
                      className={cn(
                        "text-right py-3 px-4 font-mono font-semibold",
                        bottleneck.variance_pct > 0
                          ? "text-red-600"
                          : "text-green-600",
                      )}
                    >
                      {bottleneck.variance_pct > 0 ? "+" : ""}
                      {bottleneck.variance_pct.toFixed(0)}%
                    </td>
                    <td className="text-center py-3 px-4">
                      {getBottleneckBadge(bottleneck.variance_pct)}
                    </td>
                    <td className="text-right py-3 px-4 text-gray-600 dark:text-gray-400">
                      {bottleneck.impact || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Comparison Tabs */}
      <Tabs defaultValue="category" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="category">By Category</TabsTrigger>
          <TabsTrigger value="supplier">By Supplier</TabsTrigger>
        </TabsList>

        <TabsContent value="category">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Cycle Times by Category</CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Average cycle times for top 10 spend categories
              </p>
            </CardHeader>
            <CardContent>
              {categoryChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart
                    data={categoryChartData}
                    layout="vertical"
                    margin={{ left: 150 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      stroke="#6b7280"
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fontSize: 11 }}
                      stroke="#6b7280"
                      width={140}
                    />
                    <Tooltip content={<CategoryChartTooltip />} />
                    <Bar
                      dataKey="avgDays"
                      fill="#3b82f6"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[400px] flex items-center justify-center text-gray-500">
                  No category data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="supplier">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Cycle Times by Supplier</CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Average cycle times for top 10 suppliers
              </p>
            </CardHeader>
            <CardContent>
              {supplierChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart
                    data={supplierChartData}
                    layout="vertical"
                    margin={{ left: 150 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      stroke="#6b7280"
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fontSize: 11 }}
                      stroke="#6b7280"
                      width={140}
                    />
                    <Tooltip content={<SupplierChartTooltip />} />
                    <Bar
                      dataKey="avgDays"
                      fill="#8b5cf6"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[400px] flex items-center justify-center text-gray-500">
                  No supplier data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Stage Drilldown Modal */}
      <Dialog
        open={!!selectedStage}
        onOpenChange={() => setSelectedStage(null)}
      >
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-600" />
              Stage Drilldown:{" "}
              {selectedStage?.replace(/_/g, " → ").toUpperCase()}
            </DialogTitle>
          </DialogHeader>

          {drilldownLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : stageDrilldown ? (
            <div className="space-y-6">
              {/* Stage Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                    {stageDrilldown.avg_days?.toFixed(1) || "-"}
                  </div>
                  <div className="text-sm text-blue-700 dark:text-blue-300">
                    Avg Days
                  </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                    {stageDrilldown.documents_count?.toLocaleString() || "-"}
                  </div>
                  <div className="text-sm text-purple-700 dark:text-purple-300">
                    Documents
                  </div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-900 dark:text-green-100">
                    {formatCurrency(stageDrilldown.total_value || 0)}
                  </div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    Total Value
                  </div>
                </div>
              </div>

              {/* Slowest Documents Table */}
              <div>
                <h4 className="font-semibold mb-3 text-gray-900 dark:text-gray-100">
                  Top 10 Slowest Documents
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-2 px-3 font-semibold">
                          Document
                        </th>
                        <th className="text-left py-2 px-3 font-semibold">
                          Supplier
                        </th>
                        <th className="text-right py-2 px-3 font-semibold">
                          Days
                        </th>
                        <th className="text-right py-2 px-3 font-semibold">
                          Amount
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {stageDrilldown.slowest_documents?.map((doc, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-gray-100 dark:border-gray-800"
                        >
                          <td className="py-2 px-3 font-mono">
                            {doc.document_number}
                          </td>
                          <td className="py-2 px-3">{doc.supplier_name}</td>
                          <td className="text-right py-2 px-3 font-mono text-red-600">
                            {doc.days_in_stage?.toFixed(1)}
                          </td>
                          <td className="text-right py-2 px-3">
                            {formatCurrency(doc.amount || 0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No drilldown data available
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
