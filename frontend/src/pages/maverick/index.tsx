import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  useComplianceOverview,
  useMaverickSpendAnalysis,
  usePolicyViolations,
  useViolationTrends,
  useSupplierComplianceScores,
  useSpendingPolicies,
  useResolveViolation,
  getViolationSeverityDisplay,
  getViolationTypeDisplay,
  getRiskLevelDisplay,
  getComplianceScoreColor,
  getComplianceRateStatus,
} from "@/hooks/useCompliance";
import type { ViolationSeverity, PolicyViolation } from "@/lib/api";
import {
  AlertTriangle,
  Shield,
  ShieldAlert,
  ShieldCheck,
  DollarSign,
  TrendingUp,
  Users,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  Ban,
  UserX,
  FileX,
  AlertCircle,
  CheckSquare,
  Square,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
  AreaChart,
  Area,
} from "recharts";

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

const SEVERITY_COLORS = {
  critical: "#dc2626",
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#3b82f6",
};

const CHART_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
];

function StatCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  isLoading,
  status,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
  trend?: { value: number; isPositive: boolean };
  isLoading?: boolean;
  status?: { color: string; bgColor: string };
}) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon
          className={`h-4 w-4 ${status?.color || "text-muted-foreground"}`}
        />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${status?.color || ""}`}>
          {value}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <p
            className={`text-xs ${trend.isPositive ? "text-green-600" : "text-red-600"}`}
          >
            {trend.isPositive ? "+" : ""}
            {trend.value}% from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function OverviewSection() {
  const { data: overview, isLoading } = useComplianceOverview();
  const rateStatus = overview
    ? getComplianceRateStatus(overview.compliance_rate)
    : null;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Compliance Rate"
        value={`${overview?.compliance_rate ?? 0}%`}
        icon={Shield}
        description={rateStatus?.label}
        isLoading={isLoading}
        status={
          rateStatus
            ? { color: rateStatus.color, bgColor: rateStatus.bgColor }
            : undefined
        }
      />
      <StatCard
        title="Unresolved Violations"
        value={overview?.unresolved_violations ?? 0}
        icon={ShieldAlert}
        description={`${overview?.resolved_today ?? 0} resolved today`}
        isLoading={isLoading}
        status={
          overview?.unresolved_violations && overview.unresolved_violations > 0
            ? { color: "text-red-600", bgColor: "bg-red-100" }
            : undefined
        }
      />
      <StatCard
        title="Maverick Spend"
        value={formatCurrency(overview?.maverick_spend ?? 0)}
        icon={AlertTriangle}
        description={`${overview?.maverick_percentage ?? 0}% off-contract`}
        isLoading={isLoading}
        status={
          overview?.maverick_percentage && overview.maverick_percentage > 20
            ? { color: "text-amber-600", bgColor: "bg-amber-100" }
            : undefined
        }
      />
      <StatCard
        title="Active Policies"
        value={overview?.active_policies ?? 0}
        icon={FileText}
        description="enforcing compliance"
        isLoading={isLoading}
      />
    </div>
  );
}

function SeverityBreakdownChart() {
  const { data: overview, isLoading } = useComplianceOverview();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Violation Severity</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = overview?.severity_breakdown
    ? [
        {
          name: "Critical",
          value: overview.severity_breakdown.critical,
          color: SEVERITY_COLORS.critical,
        },
        {
          name: "High",
          value: overview.severity_breakdown.high,
          color: SEVERITY_COLORS.high,
        },
        {
          name: "Medium",
          value: overview.severity_breakdown.medium,
          color: SEVERITY_COLORS.medium,
        },
        {
          name: "Low",
          value: overview.severity_breakdown.low,
          color: SEVERITY_COLORS.low,
        },
      ].filter((d) => d.value > 0)
    : [];

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5" />
          Violation Severity
        </CardTitle>
        <CardDescription>{total} total violations</CardDescription>
      </CardHeader>
      <CardContent>
        {total === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <ShieldCheck className="mx-auto h-12 w-12 mb-4 text-green-500" />
            <p>No violations detected</p>
          </div>
        ) : (
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MaverickSpendSection() {
  const { data, isLoading } = useMaverickSpendAnalysis();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Maverick Spend Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  const supplierData =
    data?.maverick_suppliers.slice(0, 10).map((s) => ({
      name:
        s.supplier_name.length > 15
          ? s.supplier_name.substring(0, 15) + "..."
          : s.supplier_name,
      spend: s.spend,
    })) ?? [];

  const categoryData =
    data?.maverick_categories.slice(0, 5).map((c) => ({
      name: c.category_name,
      spend: c.spend,
    })) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Maverick Spend Analysis
        </CardTitle>
        <CardDescription>
          {formatCurrency(data?.total_maverick_spend ?? 0)} (
          {data?.maverick_percentage ?? 0}%) off-contract
        </CardDescription>
      </CardHeader>
      <CardContent>
        {data?.maverick_suppliers.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="mx-auto h-12 w-12 mb-4 text-green-500" />
            <p>All spend is under contract</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-medium mb-3">
                Top Off-Contract Suppliers
              </h4>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={supplierData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      tickFormatter={(v) => formatCurrency(v)}
                    />
                    <YAxis type="category" dataKey="name" width={100} />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                    />
                    <Bar dataKey="spend" fill="#f59e0b" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {categoryData.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3">
                  Off-Contract by Category
                </h4>
                <div className="space-y-2">
                  {categoryData.map((cat, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between"
                    >
                      <span className="text-sm">{cat.name}</span>
                      <span className="font-medium">
                        {formatCurrency(cat.spend)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data?.recommendations && data.recommendations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3">Recommendations</h4>
                <div className="space-y-3">
                  {data.recommendations.map((rec, index) => (
                    <div
                      key={index}
                      className="p-3 rounded-lg border bg-accent/50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{rec.title}</span>
                        <Badge
                          variant={
                            rec.priority === "high"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {rec.priority}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {rec.description}
                      </p>
                      <p className="text-sm text-green-600 mt-1">
                        Potential savings:{" "}
                        {formatCurrency(rec.potential_savings)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ViolationsSection() {
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [resolvedFilter, setResolvedFilter] = useState<string>("unresolved");
  const [selectedViolation, setSelectedViolation] =
    useState<PolicyViolation | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isBatchResolveOpen, setIsBatchResolveOpen] = useState(false);
  const [batchResolutionNotes, setBatchResolutionNotes] = useState("");
  const [batchResolving, setBatchResolving] = useState(false);

  const resolvedParam =
    resolvedFilter === "all" ? undefined : resolvedFilter === "resolved";
  const severityParam =
    severityFilter === "all"
      ? undefined
      : (severityFilter as ViolationSeverity);

  const { data, isLoading } = usePolicyViolations({
    resolved: resolvedParam,
    severity: severityParam,
    limit: 50,
  });

  const resolveViolation = useResolveViolation();

  const handleResolve = async () => {
    if (!selectedViolation || !resolutionNotes.trim()) return;

    try {
      await resolveViolation.mutateAsync({
        violationId: selectedViolation.id,
        resolutionNotes: resolutionNotes.trim(),
      });
      setSelectedViolation(null);
      setResolutionNotes("");
    } catch {
      // Error handled by mutation
    }
  };

  const violations = data?.violations ?? [];
  const unresolvedViolations = violations.filter((v) => !v.is_resolved);

  // Handle select all unresolved violations
  const handleSelectAll = () => {
    if (selectedIds.size === unresolvedViolations.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(unresolvedViolations.map((v) => v.id)));
    }
  };

  // Handle individual checkbox toggle
  const handleToggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  // Handle batch resolution
  const handleBatchResolve = async () => {
    if (selectedIds.size === 0 || !batchResolutionNotes.trim()) return;

    setBatchResolving(true);
    try {
      // Resolve violations sequentially to avoid overwhelming the server
      const idsArray = Array.from(selectedIds);
      for (let i = 0; i < idsArray.length; i++) {
        await resolveViolation.mutateAsync({
          violationId: idsArray[i],
          resolutionNotes: batchResolutionNotes.trim(),
        });
      }
      setSelectedIds(new Set());
      setIsBatchResolveOpen(false);
      setBatchResolutionNotes("");
    } catch {
      // Error handled by mutation
    } finally {
      setBatchResolving(false);
    }
  };

  const getViolationIcon = (type: string) => {
    const icons: Record<string, React.ElementType> = {
      amount_exceeded: DollarSign,
      non_preferred_supplier: UserX,
      restricted_category: Ban,
      no_contract: FileX,
      approval_missing: AlertCircle,
    };
    return icons[type] || AlertTriangle;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Policy Violations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5" />
                  Policy Violations
                </CardTitle>
                <CardDescription>
                  {data?.count ?? 0} violations found
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Select
                  value={resolvedFilter}
                  onValueChange={setResolvedFilter}
                >
                  <SelectTrigger className="w-[130px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="unresolved">Unresolved</SelectItem>
                    <SelectItem value="resolved">Resolved</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={severityFilter}
                  onValueChange={setSeverityFilter}
                >
                  <SelectTrigger className="w-[130px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severity</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {/* Batch selection controls */}
            {unresolvedViolations.length > 0 && (
              <div className="flex items-center justify-between bg-muted/50 p-3 rounded-lg">
                <div className="flex items-center gap-3">
                  <Checkbox
                    id="select-all"
                    checked={
                      selectedIds.size > 0 &&
                      selectedIds.size === unresolvedViolations.length
                    }
                    onCheckedChange={handleSelectAll}
                  />
                  <label
                    htmlFor="select-all"
                    className="text-sm font-medium cursor-pointer"
                  >
                    {selectedIds.size === unresolvedViolations.length &&
                    unresolvedViolations.length > 0
                      ? "Deselect All"
                      : `Select All (${unresolvedViolations.length})`}
                  </label>
                  {selectedIds.size > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {selectedIds.size} selected
                    </Badge>
                  )}
                </div>
                {selectedIds.size > 0 && (
                  <Button size="sm" onClick={() => setIsBatchResolveOpen(true)}>
                    <CheckSquare className="h-4 w-4 mr-2" />
                    Resolve Selected ({selectedIds.size})
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {violations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <ShieldCheck className="mx-auto h-12 w-12 mb-4 text-green-500" />
              <p>No violations match your filters</p>
            </div>
          ) : (
            <div className="space-y-3">
              {violations.map((violation) => {
                const severityDisplay = getViolationSeverityDisplay(
                  violation.severity,
                );
                const typeDisplay = getViolationTypeDisplay(
                  violation.violation_type,
                );
                const ViolationIcon = getViolationIcon(
                  violation.violation_type,
                );

                return (
                  <div
                    key={violation.id}
                    className={`p-4 rounded-lg border ${violation.is_resolved ? "bg-muted/30" : "bg-card"} ${selectedIds.has(violation.id) ? "ring-2 ring-primary" : ""}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {/* Checkbox for unresolved violations */}
                        {!violation.is_resolved && (
                          <Checkbox
                            checked={selectedIds.has(violation.id)}
                            onCheckedChange={() =>
                              handleToggleSelect(violation.id)
                            }
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                        <ViolationIcon
                          className={`h-4 w-4 ${severityDisplay.color}`}
                        />
                        <span className="font-medium">{typeDisplay.label}</span>
                        <Badge
                          className={`${severityDisplay.color} ${severityDisplay.bgColor}`}
                        >
                          {severityDisplay.label}
                        </Badge>
                        {violation.is_resolved && (
                          <Badge variant="outline" className="text-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Resolved
                          </Badge>
                        )}
                      </div>
                      {!violation.is_resolved && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedViolation(violation)}
                        >
                          Resolve
                        </Button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Amount:</span>
                        <span className="ml-1 font-medium">
                          {formatCurrency(violation.transaction_amount)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Supplier:</span>
                        <span className="ml-1">{violation.supplier_name}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Category:</span>
                        <span className="ml-1">{violation.category_name}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Policy:</span>
                        <span className="ml-1">{violation.policy_name}</span>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      <Clock className="inline h-3 w-3 mr-1" />
                      {new Date(violation.created_at).toLocaleDateString()}
                    </div>
                    {violation.is_resolved && violation.resolution_notes && (
                      <div className="mt-2 text-sm text-muted-foreground border-t pt-2">
                        <span className="font-medium">Resolution:</span>{" "}
                        {violation.resolution_notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Single violation resolve dialog */}
      <Dialog
        open={!!selectedViolation}
        onOpenChange={() => setSelectedViolation(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Violation</DialogTitle>
            <DialogDescription>
              Provide notes explaining how this violation was resolved.
            </DialogDescription>
          </DialogHeader>
          {selectedViolation && (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-muted">
                <div className="font-medium">
                  {
                    getViolationTypeDisplay(selectedViolation.violation_type)
                      .label
                  }
                </div>
                <div className="text-sm text-muted-foreground">
                  {selectedViolation.supplier_name} •{" "}
                  {formatCurrency(selectedViolation.transaction_amount)}
                </div>
              </div>
              <Textarea
                placeholder="Enter resolution notes..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
              />
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSelectedViolation(null)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleResolve}
              disabled={!resolutionNotes.trim() || resolveViolation.isPending}
            >
              {resolveViolation.isPending ? "Resolving..." : "Resolve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch resolve dialog */}
      <Dialog open={isBatchResolveOpen} onOpenChange={setIsBatchResolveOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              Resolve {selectedIds.size} Violations
            </DialogTitle>
            <DialogDescription>
              Apply the same resolution notes to all selected violations.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="max-h-48 overflow-y-auto space-y-2">
              {Array.from(selectedIds).map((id) => {
                const violation = violations.find((v) => v.id === id);
                if (!violation) return null;
                return (
                  <div
                    key={id}
                    className="p-2 rounded bg-muted text-sm flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Badge
                        className={`${getViolationSeverityDisplay(violation.severity).bgColor} ${getViolationSeverityDisplay(violation.severity).color} text-xs`}
                      >
                        {violation.severity}
                      </Badge>
                      <span>
                        {
                          getViolationTypeDisplay(violation.violation_type)
                            .label
                        }
                      </span>
                    </div>
                    <span className="text-muted-foreground">
                      {formatCurrency(violation.transaction_amount)}
                    </span>
                  </div>
                );
              })}
            </div>
            <Textarea
              placeholder="Enter resolution notes for all selected violations..."
              value={batchResolutionNotes}
              onChange={(e) => setBatchResolutionNotes(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsBatchResolveOpen(false)}
              disabled={batchResolving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleBatchResolve}
              disabled={!batchResolutionNotes.trim() || batchResolving}
            >
              {batchResolving
                ? `Resolving ${selectedIds.size}...`
                : `Resolve All (${selectedIds.size})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function ViolationTrendsSection() {
  const { data, isLoading } = useViolationTrends(12);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Violation Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  const trendData = data?.monthly_trend ?? [];
  const typeData = data?.by_type
    ? Object.entries(data.by_type)
        .map(([type, count]) => ({
          name: getViolationTypeDisplay(type as any).label,
          value: count,
        }))
        .filter((d) => d.value > 0)
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Violation Trends
        </CardTitle>
        <CardDescription>Monthly violation patterns</CardDescription>
      </CardHeader>
      <CardContent>
        {trendData.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <ShieldCheck className="mx-auto h-12 w-12 mb-4 text-green-500" />
            <p>No violation history</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke="#ef4444"
                    fill="#fecaca"
                  />
                  <Area
                    type="monotone"
                    dataKey="resolved"
                    name="Resolved"
                    stroke="#22c55e"
                    fill="#bbf7d0"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {typeData.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-3">Violations by Type</h4>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={typeData}
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        dataKey="value"
                        label={({ name, percent }) =>
                          `${name} ${(percent * 100).toFixed(0)}%`
                        }
                      >
                        {typeData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SupplierComplianceSection() {
  const { data, isLoading } = useSupplierComplianceScores();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Supplier Compliance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const suppliers = data?.suppliers ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Supplier Compliance Leaderboard
        </CardTitle>
        <CardDescription>Suppliers ranked by compliance score</CardDescription>
      </CardHeader>
      <CardContent>
        {suppliers.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Users className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No supplier data available</p>
          </div>
        ) : (
          <div className="space-y-3">
            {suppliers.slice(0, 10).map((supplier, index) => {
              const riskDisplay = getRiskLevelDisplay(supplier.risk_level);

              return (
                <div
                  key={supplier.supplier_id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-muted-foreground w-6">
                      {index + 1}
                    </span>
                    <div>
                      <div className="font-medium">
                        {supplier.supplier_name}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {supplier.transaction_count} transactions •{" "}
                        {formatCurrency(supplier.total_spend)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div
                        className={`text-xl font-bold ${getComplianceScoreColor(supplier.compliance_score)}`}
                      >
                        {supplier.compliance_score.toFixed(0)}
                      </div>
                      <div className="text-xs text-muted-foreground">score</div>
                    </div>
                    <Badge
                      className={`${riskDisplay.color} ${riskDisplay.bgColor}`}
                    >
                      {riskDisplay.label}
                    </Badge>
                    {supplier.has_contract && (
                      <Badge variant="outline" className="text-green-600">
                        <FileText className="h-3 w-3 mr-1" />
                        Contract
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PoliciesSection() {
  const { data, isLoading } = useSpendingPolicies();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Spending Policies</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const policies = data?.policies ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Spending Policies
        </CardTitle>
        <CardDescription>{policies.length} active policies</CardDescription>
      </CardHeader>
      <CardContent>
        {policies.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No policies configured</p>
            <p className="text-sm">Policies can be created in Django Admin</p>
          </div>
        ) : (
          <div className="space-y-4">
            {policies.map((policy) => (
              <div key={policy.id} className="p-4 rounded-lg border">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium">{policy.name}</div>
                    {policy.description && (
                      <div className="text-sm text-muted-foreground">
                        {policy.description}
                      </div>
                    )}
                  </div>
                  <Badge variant={policy.is_active ? "default" : "secondary"}>
                    {policy.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {policy.rules_summary.map((rule, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {rule}
                    </Badge>
                  ))}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {policy.violation_count} violations detected
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function MaverickPage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Shield className="h-8 w-8 text-amber-600" />
          Maverick Spend & Compliance
        </h1>
        <p className="text-muted-foreground mt-1">
          Track policy violations, monitor off-contract spending, and ensure
          compliance
        </p>
      </div>

      <OverviewSection />

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList>
          <TabsTrigger value="overview">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Maverick Spend
          </TabsTrigger>
          <TabsTrigger value="violations">
            <ShieldAlert className="h-4 w-4 mr-2" />
            Violations
          </TabsTrigger>
          <TabsTrigger value="trends">
            <TrendingUp className="h-4 w-4 mr-2" />
            Trends
          </TabsTrigger>
          <TabsTrigger value="suppliers">
            <Users className="h-4 w-4 mr-2" />
            Suppliers
          </TabsTrigger>
          <TabsTrigger value="policies">
            <FileText className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 md:grid-cols-2">
            <MaverickSpendSection />
            <SeverityBreakdownChart />
          </div>
        </TabsContent>

        <TabsContent value="violations">
          <ViolationsSection />
        </TabsContent>

        <TabsContent value="trends">
          <ViolationTrendsSection />
        </TabsContent>

        <TabsContent value="suppliers">
          <SupplierComplianceSection />
        </TabsContent>

        <TabsContent value="policies">
          <PoliciesSection />
        </TabsContent>
      </Tabs>
    </div>
  );
}
