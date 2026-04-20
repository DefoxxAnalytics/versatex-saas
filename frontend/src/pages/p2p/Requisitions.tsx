import { useState } from "react";
import {
  usePROverview,
  usePRApprovalAnalysis,
  usePRByDepartment,
  usePRPending,
  usePRDetail,
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
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  FunnelChart,
  Funnel,
  LabelList,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Building2,
  TrendingUp,
  AlertTriangle,
  Users,
  Loader2,
  Eye,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// Custom tooltip for department pie chart
interface DepartmentData {
  name: string;
  value: number;
  amount: number;
  color: string;
}

const DepartmentTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as DepartmentData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        PRs: {data.value.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Amount: {formatCurrency(data.amount)}
      </div>
    </div>
  );
};

// Custom tooltip for approval time chart
interface ApprovalTimeData {
  name: string;
  count: number;
  percent: number;
  color: string;
}

const ApprovalTimeTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as ApprovalTimeData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.name}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Count: {data.count.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Percentage: {data.percent?.toFixed(1)}%
      </div>
    </div>
  );
};

/**
 * Purchase Requisition Analysis - PR patterns, approval efficiency, and conversion rates
 * Shows PR volume, approval times, department patterns, and pending items
 */
export default function Requisitions() {
  const { data: prOverview, isLoading: overviewLoading } = usePROverview();
  const { data: approvalAnalysis, isLoading: approvalLoading } =
    usePRApprovalAnalysis();
  const { data: prByDepartment, isLoading: deptLoading } = usePRByDepartment();
  const { data: prPending, isLoading: pendingLoading } = usePRPending();

  const [selectedPRId, setSelectedPRId] = useState<number | null>(null);
  const { data: prDetail, isLoading: detailLoading } =
    usePRDetail(selectedPRId);

  const isLoading =
    overviewLoading || approvalLoading || deptLoading || pendingLoading;

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
          <SkeletonChart height={300} type="bar" />
          <SkeletonChart height={300} type="pie" />
        </div>
      </div>
    );
  }

  // No data state
  if (!prOverview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <ClipboardList className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No PR Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload purchase requisition data to see analysis.
          </p>
        </div>
      </div>
    );
  }

  // KPI Cards data
  const kpis = [
    {
      label: "Total PRs",
      value: prOverview.total_count?.toLocaleString() || "0",
      icon: ClipboardList,
      color: "blue",
      subtext: `${formatCurrency(prOverview.total_value || 0)} total value`,
    },
    {
      label: "Conversion Rate",
      value: `${prOverview.conversion_rate?.toFixed(1) || 0}%`,
      icon: ArrowRight,
      color: "green",
      subtext: "PR → PO",
    },
    {
      label: "Avg Approval Time",
      value: `${prOverview.avg_approval_days?.toFixed(1) || 0} days`,
      icon: Clock,
      color: "purple",
      subtext: `Target: 2 days`,
    },
    {
      label: "Rejection Rate",
      value: `${prOverview.rejection_rate?.toFixed(1) || 0}%`,
      icon: XCircle,
      color: "red",
      subtext: `Rejected PRs`,
    },
  ];

  // PR Status funnel data using status_breakdown
  const statusCounts = prOverview.status_breakdown || {};
  const funnelData = [
    { name: "Created", value: prOverview.total_count || 0, fill: "#3b82f6" },
    {
      name: "Pending",
      value: statusCounts["pending_approval"] || 0,
      fill: "#8b5cf6",
    },
    { name: "Approved", value: statusCounts["approved"] || 0, fill: "#10b981" },
    {
      name: "Converted",
      value: statusCounts["converted_to_po"] || 0,
      fill: "#06b6d4",
    },
  ];

  // Department pie chart data
  const departmentData =
    prByDepartment?.map((dept) => ({
      name: dept.department,
      value: dept.count,
      amount: dept.total_value,
      color: getRandomColor(dept.department),
    })) || [];

  // Approval time distribution data
  const approvalTimeData =
    approvalAnalysis?.approval_time_distribution?.map((item) => ({
      name: item.range,
      count: item.count,
      percent: item.percentage,
      color: getApprovalTimeColor(item.range),
    })) || [];

  // Get color based on approval time bucket
  function getApprovalTimeColor(bucket: string): string {
    const colors: Record<string, string> = {
      same_day: "#10b981",
      "1_day": "#22c55e",
      "2_3_days": "#3b82f6",
      "4_7_days": "#f59e0b",
      "7_plus": "#ef4444",
    };
    return colors[bucket] || "#6b7280";
  }

  // Generate consistent color from string
  function getRandomColor(str: string): string {
    const colors = [
      "#3b82f6",
      "#8b5cf6",
      "#ec4899",
      "#f59e0b",
      "#10b981",
      "#06b6d4",
      "#6366f1",
      "#f97316",
    ];
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }

  // PR status badge
  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
      pending_approval:
        "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
      approved:
        "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
      rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
      converted_to_po:
        "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
      cancelled:
        "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
    };
    return styles[status] || styles.draft;
  };

  // Priority badge
  const getPriorityBadge = (priority: string) => {
    const styles: Record<string, string> = {
      low: "bg-gray-100 text-gray-600",
      normal: "bg-blue-100 text-blue-600",
      high: "bg-orange-100 text-orange-600",
      urgent: "bg-red-100 text-red-600",
    };
    return styles[priority] || styles.normal;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center gap-3 mb-6">
        <ClipboardList className="h-8 w-8 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Purchase Requisition Analysis
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            PR patterns, approval efficiency, and conversion rates
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
                kpi.color === "red" && "border-l-red-500",
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
                      kpi.color === "red" && "text-red-600",
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
        {/* PR Status Funnel */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>PR Status Funnel</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Requisition flow through stages
            </p>
          </CardHeader>
          <CardContent>
            {funnelData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <FunnelChart>
                  <Tooltip
                    formatter={(value: number) => [
                      value.toLocaleString(),
                      "PRs",
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

        {/* PRs by Department */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-purple-600" />
              <CardTitle>PRs by Department</CardTitle>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Requisition distribution by department
            </p>
          </CardHeader>
          <CardContent>
            {departmentData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={departmentData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) =>
                      `${name}: ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    {departmentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<DepartmentTooltip />} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No department data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Approval Time Distribution */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-600" />
            <CardTitle>Approval Time Distribution</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            How long PRs take to get approved
          </p>
        </CardHeader>
        <CardContent>
          {approvalTimeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={approvalTimeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  stroke="#6b7280"
                />
                <YAxis tick={{ fontSize: 11 }} stroke="#6b7280" />
                <Tooltip content={<ApprovalTimeTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {approvalTimeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No approval time data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Approvals Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            <CardTitle>Pending Approvals</CardTitle>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            PRs awaiting approval - oldest first
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    PR #
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Requestor
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Department
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Amount
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Priority
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Days Pending
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {pendingLoading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-blue-600" />
                    </td>
                  </tr>
                ) : prPending?.pending_prs?.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">
                      No pending approvals
                    </td>
                  </tr>
                ) : (
                  prPending?.pending_prs?.map((pr) => (
                    <tr
                      key={pr.pr_id}
                      className={cn(
                        "border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors",
                        pr.days_pending > 5 && "bg-red-50 dark:bg-red-900/10",
                      )}
                    >
                      <td className="py-3 px-4 font-mono text-sm">
                        {pr.pr_number}
                      </td>
                      <td className="py-3 px-4 text-sm">{pr.requestor}</td>
                      <td className="py-3 px-4 text-sm">{pr.department}</td>
                      <td className="text-right py-3 px-4 font-mono">
                        {formatCurrency(pr.amount)}
                      </td>
                      <td className="text-center py-3 px-4">
                        <Badge className={getPriorityBadge(pr.priority)}>
                          {pr.priority}
                        </Badge>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Badge
                          variant={
                            pr.days_pending > 5
                              ? "destructive"
                              : pr.days_pending > 2
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {pr.days_pending}d
                        </Badge>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedPRId(pr.pr_id)}
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

      {/* PR Detail Modal */}
      <Dialog open={!!selectedPRId} onOpenChange={() => setSelectedPRId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-blue-600" />
              Purchase Requisition Detail
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : prDetail ? (
            <div className="space-y-6">
              {/* Header Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    PR Number
                  </label>
                  <p className="font-mono text-lg">{prDetail.pr_number}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Status
                  </label>
                  <div className="mt-1">
                    <Badge className={getStatusBadge(prDetail.status)}>
                      {prDetail.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Requestor
                  </label>
                  <p className="text-lg">{prDetail.requestor_name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Department
                  </label>
                  <p className="text-lg">{prDetail.department}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Estimated Amount
                  </label>
                  <p className="text-lg font-semibold">
                    {formatCurrency(prDetail.estimated_amount)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Priority
                  </label>
                  <div className="mt-1">
                    <Badge className={getPriorityBadge(prDetail.priority)}>
                      {prDetail.priority}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Dates */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold mb-3">Timeline</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Created</div>
                    <div className="font-medium">
                      {prDetail.created_date || "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Submitted</div>
                    <div className="font-medium">
                      {prDetail.submitted_date || "-"}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Approved</div>
                    <div className="font-medium">
                      {prDetail.approval_date || "-"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              {prDetail.description && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Description
                  </label>
                  <p className="mt-1 text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                    {prDetail.description}
                  </p>
                </div>
              )}

              {/* Suggested Supplier */}
              {prDetail.suggested_supplier && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Suggested Supplier
                  </label>
                  <p className="text-lg">{prDetail.suggested_supplier}</p>
                </div>
              )}

              {/* Linked PO */}
              {prDetail.linked_po_number && (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="font-semibold text-green-800 dark:text-green-200">
                      Converted to PO: {prDetail.linked_po_number}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              PR detail not found
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
