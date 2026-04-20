import { useState } from "react";
import {
  useMatchingOverview,
  useMatchingExceptions,
  useExceptionsByType,
  useExceptionsBySupplier,
  usePriceVarianceAnalysis,
  useQuantityVarianceAnalysis,
  useInvoiceMatchDetail,
  useResolveException,
  useBulkResolveExceptions,
} from "@/hooks/useP2PAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
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
  Scale,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  DollarSign,
  FileQuestion,
  Clock,
  Loader2,
  Eye,
  CheckSquare,
  Filter,
} from "lucide-react";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import { formatCurrency } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import type { ExceptionType, InvoiceException } from "@/lib/api";
import { toast } from "sonner";

// Custom tooltip for supplier exception chart
interface SupplierExceptionData {
  name: string;
  fullName: string;
  exceptions: number;
  amount: number;
  rate: number;
}

const SupplierExceptionTooltip = ({
  active,
  payload,
}: TooltipProps<ValueType, NameType>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0].payload as SupplierExceptionData;
  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <div className="font-semibold text-gray-900 dark:text-gray-100">
        {data.fullName}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Exceptions: {data.exceptions.toLocaleString()}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Amount: {formatCurrency(data.amount)}
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Rate: {data.rate.toFixed(1)}%
      </div>
    </div>
  );
};

/**
 * 3-Way Match Center - Invoice matching analysis and exception management
 * Shows PO vs Receipt vs Invoice matching status and exception handling
 */
export default function Matching() {
  const { data: matchingOverview, isLoading: overviewLoading } =
    useMatchingOverview();
  const { data: exceptionsByType, isLoading: typeLoading } =
    useExceptionsByType();
  const { data: exceptionsBySupplier, isLoading: supplierLoading } =
    useExceptionsBySupplier();
  const { data: priceVariance, isLoading: priceLoading } =
    usePriceVarianceAnalysis();
  const { data: quantityVariance, isLoading: qtyLoading } =
    useQuantityVarianceAnalysis();

  // Exception list with filters
  const [exceptionFilters, setExceptionFilters] = useState<{
    exception_type?: ExceptionType;
    status?: "open" | "resolved" | "all";
    limit?: number;
  }>({});
  const { data: exceptions, isLoading: exceptionsLoading } =
    useMatchingExceptions(exceptionFilters);

  // Selected invoice for detail view
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(
    null,
  );
  const { data: invoiceDetail, isLoading: detailLoading } =
    useInvoiceMatchDetail(selectedInvoiceId);

  // Bulk selection state
  const [selectedExceptions, setSelectedExceptions] = useState<number[]>([]);
  const [showBulkResolve, setShowBulkResolve] = useState(false);
  const [bulkResolutionNotes, setBulkResolutionNotes] = useState("");

  // Single resolve state
  const [showResolve, setShowResolve] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Mutations
  const resolveException = useResolveException();
  const bulkResolve = useBulkResolveExceptions();

  const isLoading =
    overviewLoading ||
    typeLoading ||
    supplierLoading ||
    priceLoading ||
    qtyLoading;

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
  if (!matchingOverview) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <div className="text-center">
          <Scale className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            No Matching Data Available
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Upload invoice, PO, and goods receipt data to see matching analysis.
          </p>
        </div>
      </div>
    );
  }

  // Handle single exception resolution
  const handleResolve = async () => {
    if (!selectedInvoiceId || !resolutionNotes.trim()) {
      toast.error("Please provide resolution notes");
      return;
    }

    try {
      await resolveException.mutateAsync({
        invoiceId: selectedInvoiceId,
        resolutionNotes: resolutionNotes.trim(),
      });
      toast.success("Exception resolved successfully");
      setShowResolve(false);
      setResolutionNotes("");
      setSelectedInvoiceId(null);
    } catch {
      toast.error("Failed to resolve exception");
    }
  };

  // Handle bulk resolution
  const handleBulkResolve = async () => {
    if (selectedExceptions.length === 0 || !bulkResolutionNotes.trim()) {
      toast.error("Please select exceptions and provide resolution notes");
      return;
    }

    try {
      await bulkResolve.mutateAsync({
        invoiceIds: selectedExceptions,
        resolutionNotes: bulkResolutionNotes.trim(),
      });
      toast.success(
        `${selectedExceptions.length} exceptions resolved successfully`,
      );
      setShowBulkResolve(false);
      setBulkResolutionNotes("");
      setSelectedExceptions([]);
    } catch {
      toast.error("Failed to resolve exceptions");
    }
  };

  // Toggle exception selection
  const toggleException = (invoiceId: number) => {
    setSelectedExceptions((prev) =>
      prev.includes(invoiceId)
        ? prev.filter((id) => id !== invoiceId)
        : [...prev, invoiceId],
    );
  };

  // Select all visible exceptions
  const toggleSelectAll = () => {
    if (!exceptions?.exceptions) return;
    const allIds = exceptions.exceptions.map((e) => e.invoice_id);
    if (selectedExceptions.length === allIds.length) {
      setSelectedExceptions([]);
    } else {
      setSelectedExceptions(allIds);
    }
  };

  // KPI Cards data
  const kpis = [
    {
      label: "3-Way Match Rate",
      value: `${matchingOverview.three_way_matched.percentage?.toFixed(1) || 0}%`,
      icon: CheckCircle2,
      color: "green",
      subtext: `${matchingOverview.three_way_matched.count?.toLocaleString() || 0} invoices`,
    },
    {
      label: "Open Exceptions",
      value: matchingOverview.exceptions.count?.toLocaleString() || "0",
      icon: AlertTriangle,
      color: "orange",
      subtext: `${formatCurrency(matchingOverview.exceptions.amount || 0)} at risk`,
    },
    {
      label: "Exception Amount",
      value: formatCurrency(matchingOverview.exceptions.amount || 0),
      icon: DollarSign,
      color: "red",
      subtext: `${matchingOverview.exceptions.percentage?.toFixed(1) || 0}% of total`,
    },
    {
      label: "Avg Resolution Time",
      value: `${matchingOverview.avg_resolution_days?.toFixed(1) || 0} days`,
      icon: Clock,
      color: "blue",
      subtext: "Target: 5 days",
    },
  ];

  // Match status pie chart data
  const matchStatusData = [
    {
      name: "3-Way Matched",
      value: matchingOverview.three_way_matched.count || 0,
      color: "#10b981",
    },
    {
      name: "2-Way Matched",
      value: matchingOverview.two_way_matched.count || 0,
      color: "#3b82f6",
    },
    {
      name: "Exceptions",
      value: matchingOverview.exceptions.count || 0,
      color: "#ef4444",
    },
  ];

  // Exception type bar chart data
  const exceptionTypeData =
    exceptionsByType?.map((type) => ({
      name: type.exception_type
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l: string) => l.toUpperCase()),
      count: type.count,
      amount: type.amount,
    })) || [];

  // Supplier exception data
  const supplierExceptionData =
    exceptionsBySupplier?.slice(0, 10).map((sup) => ({
      name:
        sup.supplier.length > 20
          ? sup.supplier.substring(0, 20) + "..."
          : sup.supplier,
      fullName: sup.supplier,
      exceptions: sup.exception_count,
      amount: sup.exception_amount,
      rate: sup.exception_rate,
    })) || [];

  // Get exception type badge
  const getExceptionBadge = (type: ExceptionType) => {
    const styles: Record<ExceptionType, string> = {
      price_variance:
        "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
      quantity_variance:
        "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
      no_po:
        "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
      duplicate:
        "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
      missing_gr:
        "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
      other: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
    };
    return styles[type] || styles.other;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Scale className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              3-Way Match Center
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              PO vs Receipt vs Invoice matching and exception management
            </p>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedExceptions.length > 0 && (
          <Button
            onClick={() => setShowBulkResolve(true)}
            className="bg-green-600 hover:bg-green-700"
          >
            <CheckSquare className="h-4 w-4 mr-2" />
            Resolve {selectedExceptions.length} Selected
          </Button>
        )}
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
                kpi.color === "green" && "border-l-green-500",
                kpi.color === "orange" && "border-l-orange-500",
                kpi.color === "red" && "border-l-red-500",
                kpi.color === "blue" && "border-l-blue-500",
              )}
            >
              <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-2">
                  <Icon
                    className={cn(
                      "h-5 w-5",
                      kpi.color === "green" && "text-green-600",
                      kpi.color === "orange" && "text-orange-600",
                      kpi.color === "red" && "text-red-600",
                      kpi.color === "blue" && "text-blue-600",
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
        {/* Match Status Pie */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>Match Status Distribution</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Invoice matching breakdown by status
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={matchStatusData}
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
                  {matchStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => [
                    value.toLocaleString(),
                    "Invoices",
                  ]}
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    borderRadius: "8px",
                    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Exception by Type Bar */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle>Exceptions by Type</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Count and amount by exception category
            </p>
          </CardHeader>
          <CardContent>
            {exceptionTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={exceptionTypeData}
                  layout="vertical"
                  margin={{ left: 100 }}
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
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                    formatter={(value: number, name: string) => [
                      name === "count"
                        ? value.toLocaleString()
                        : formatCurrency(value),
                      name === "count" ? "Count" : "Amount",
                    ]}
                  />
                  <Legend />
                  <Bar
                    dataKey="count"
                    name="Count"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-500">
                No exception data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Supplier Exception Analysis */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Exceptions by Supplier</CardTitle>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Top suppliers with highest exception rates
          </p>
        </CardHeader>
        <CardContent>
          {supplierExceptionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={supplierExceptionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  stroke="#6b7280"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 11 }}
                  stroke="#6b7280"
                />
                <Tooltip content={<SupplierExceptionTooltip />} />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="exceptions"
                  name="Exceptions"
                  fill="#ef4444"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  yAxisId="right"
                  dataKey="rate"
                  name="Exception Rate %"
                  fill="#f59e0b"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[350px] flex items-center justify-center text-gray-500">
              No supplier exception data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exception List with Filters */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Exception Queue</CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Open exceptions requiring resolution
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <Select
                value={exceptionFilters.exception_type || "all"}
                onValueChange={(value) =>
                  setExceptionFilters({
                    ...exceptionFilters,
                    exception_type:
                      value === "all" ? undefined : (value as ExceptionType),
                  })
                }
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Exception Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="price_variance">Price Variance</SelectItem>
                  <SelectItem value="quantity_variance">
                    Quantity Variance
                  </SelectItem>
                  <SelectItem value="no_po">No PO</SelectItem>
                  <SelectItem value="duplicate">Duplicate</SelectItem>
                  <SelectItem value="missing_gr">Missing GR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-2">
                    <Checkbox
                      checked={
                        (exceptions?.exceptions?.length ?? 0) > 0 &&
                        selectedExceptions.length ===
                          (exceptions?.exceptions?.length ?? 0)
                      }
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Invoice #
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Supplier
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Type
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Amount
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Variance
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Age
                  </th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {exceptionsLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-blue-600" />
                    </td>
                  </tr>
                ) : exceptions?.exceptions?.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-gray-500">
                      No open exceptions
                    </td>
                  </tr>
                ) : (
                  exceptions?.exceptions?.map((exception) => (
                    <tr
                      key={exception.invoice_id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-2">
                        <Checkbox
                          checked={selectedExceptions.includes(
                            exception.invoice_id,
                          )}
                          onCheckedChange={() =>
                            toggleException(exception.invoice_id)
                          }
                        />
                      </td>
                      <td className="py-3 px-4 font-mono text-sm">
                        {exception.invoice_number}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        {exception.supplier}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          className={getExceptionBadge(
                            exception.exception_type,
                          )}
                        >
                          {exception.exception_type.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="text-right py-3 px-4 font-mono">
                        {formatCurrency(exception.invoice_amount)}
                      </td>
                      <td className="text-right py-3 px-4 font-mono text-red-600">
                        {formatCurrency(exception.exception_amount || 0)}
                      </td>
                      <td className="text-center py-3 px-4">
                        <Badge
                          variant={
                            exception.days_open > 10
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {exception.days_open}d
                        </Badge>
                      </td>
                      <td className="text-center py-3 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setSelectedInvoiceId(exception.invoice_id)
                          }
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

      {/* Invoice Detail Modal */}
      <Dialog
        open={!!selectedInvoiceId}
        onOpenChange={() => setSelectedInvoiceId(null)}
      >
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileQuestion className="h-5 w-5 text-blue-600" />
              Invoice Match Detail
            </DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : invoiceDetail ? (
            <div className="space-y-6">
              {/* Invoice Header */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Invoice Number
                  </label>
                  <p className="font-mono text-lg">
                    {invoiceDetail.invoice.invoice_number}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Supplier
                  </label>
                  <p className="text-lg">{invoiceDetail.invoice.supplier}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Invoice Amount
                  </label>
                  <p className="text-lg font-semibold">
                    {formatCurrency(invoiceDetail.invoice.invoice_amount)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Exception Type
                  </label>
                  {invoiceDetail.invoice.exception_type && (
                    <Badge
                      className={getExceptionBadge(
                        invoiceDetail.invoice.exception_type,
                      )}
                    >
                      {invoiceDetail.invoice.exception_type.replace(/_/g, " ")}
                    </Badge>
                  )}
                </div>
              </div>

              {/* 3-Way Match Comparison */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold mb-3">3-Way Match Comparison</h4>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="bg-white dark:bg-gray-700 rounded-lg p-3">
                    <div className="text-sm text-gray-500 mb-1">PO Amount</div>
                    <div className="font-mono font-semibold">
                      {formatCurrency(
                        invoiceDetail.purchase_order?.total_amount || 0,
                      )}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-700 rounded-lg p-3">
                    <div className="text-sm text-gray-500 mb-1">
                      GR Quantity
                    </div>
                    <div className="font-mono font-semibold">
                      {invoiceDetail.goods_receipt?.quantity_received || 0}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-700 rounded-lg p-3">
                    <div className="text-sm text-gray-500 mb-1">
                      Invoice Amount
                    </div>
                    <div className="font-mono font-semibold">
                      {formatCurrency(invoiceDetail.invoice.invoice_amount)}
                    </div>
                  </div>
                </div>
                {invoiceDetail.variance.total_variance && (
                  <div className="mt-3 text-center">
                    <span className="text-sm text-gray-500">Variance: </span>
                    <span className="font-mono font-semibold text-red-600">
                      {formatCurrency(invoiceDetail.variance.total_variance)}
                    </span>
                  </div>
                )}
              </div>

              {/* Exception Notes */}
              {invoiceDetail.invoice.exception_notes && (
                <div>
                  <label className="text-sm font-medium text-gray-500">
                    Exception Notes
                  </label>
                  <p className="mt-1 text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                    {invoiceDetail.invoice.exception_notes}
                  </p>
                </div>
              )}

              {/* Resolve Button */}
              {!invoiceDetail.invoice.exception_resolved &&
                invoiceDetail.invoice.has_exception && (
                  <Button
                    onClick={() => setShowResolve(true)}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Resolve Exception
                  </Button>
                )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Invoice detail not found
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Single Resolve Modal */}
      <Dialog open={showResolve} onOpenChange={setShowResolve}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Exception</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Resolution Notes
              </label>
              <Textarea
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Enter resolution details..."
                rows={4}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResolve(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleResolve}
              disabled={resolveException.isPending || !resolutionNotes.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              {resolveException.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Resolve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Resolve Modal */}
      <Dialog open={showBulkResolve} onOpenChange={setShowBulkResolve}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Bulk Resolve {selectedExceptions.length} Exceptions
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              You are about to resolve {selectedExceptions.length} selected
              exceptions. This action cannot be undone.
            </p>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Resolution Notes
              </label>
              <Textarea
                value={bulkResolutionNotes}
                onChange={(e) => setBulkResolutionNotes(e.target.value)}
                placeholder="Enter resolution details for all selected exceptions..."
                rows={4}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkResolve(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleBulkResolve}
              disabled={bulkResolve.isPending || !bulkResolutionNotes.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              {bulkResolve.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Resolve All
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
