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
  useContractOverview,
  useContracts,
  useContractDetail,
  useExpiringContracts,
  useContractSavings,
  useContractRenewals,
  useContractVsActual,
  getContractStatusDisplay,
  getRecommendationDisplay,
  getUtilizationStatus,
  formatDaysUntilExpiry,
  getSavingsTypeDisplay,
} from "@/hooks/useContracts";
import {
  FileText,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Clock,
  BarChart3,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
  Calendar,
  Building2,
  PiggyBank,
  X,
  Info,
  Users,
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
} from "recharts";

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

const COLORS = [
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
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
  trend?: { value: number; isPositive: boolean };
  isLoading?: boolean;
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
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
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
  const { data: overview, isLoading } = useContractOverview();

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Contracts"
        value={overview?.total_contracts ?? 0}
        icon={FileText}
        description={`${overview?.active_contracts ?? 0} active`}
        isLoading={isLoading}
      />
      <StatCard
        title="Total Contract Value"
        value={formatCurrency(overview?.total_value ?? 0)}
        icon={DollarSign}
        description={`${formatCurrency(overview?.annual_value ?? 0)}/year`}
        isLoading={isLoading}
      />
      <StatCard
        title="Contract Coverage"
        value={`${(overview?.coverage_percentage ?? 0).toFixed(1)}%`}
        icon={BarChart3}
        description="of spend under contract"
        isLoading={isLoading}
      />
      <StatCard
        title="Expiring Soon"
        value={overview?.expiring_soon ?? 0}
        icon={AlertTriangle}
        description="within 90 days"
        isLoading={isLoading}
      />
    </div>
  );
}

function ContractDetailModal({
  contractId,
  isOpen,
  onClose,
}: {
  contractId: number | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  const { data: contract, isLoading } = useContractDetail(contractId);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Contract Details
          </DialogTitle>
          <DialogDescription>
            Full contract information and performance metrics
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : !contract ? (
          <div className="text-center py-8 text-muted-foreground">
            <Info className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>Contract details not available</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header Info */}
            <div className="border-b pb-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">{contract.title}</h3>
                <Badge
                  className={`${getContractStatusDisplay(contract.status).color} ${getContractStatusDisplay(contract.status).bgColor}`}
                >
                  {getContractStatusDisplay(contract.status).label}
                </Badge>
              </div>
              <div className="text-sm text-muted-foreground">
                <span>{contract.contract_number}</span>
                <span className="mx-2">•</span>
                <span>{contract.supplier_name}</span>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Total Value</div>
                <div className="text-lg font-bold">
                  {formatCurrency(contract.total_value)}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">
                  Actual Spend
                </div>
                <div className="text-lg font-bold">
                  {formatCurrency(contract.actual_spend || 0)}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Remaining</div>
                <div className="text-lg font-bold text-green-600">
                  {formatCurrency(contract.remaining_value || 0)}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-muted/50">
                <div className="text-xs text-muted-foreground">Utilization</div>
                <div
                  className={`text-lg font-bold ${getUtilizationStatus(contract.utilization_percentage).color}`}
                >
                  {contract.utilization_percentage.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Utilization Progress */}
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-muted-foreground">
                  Contract Utilization
                </span>
                <span
                  className={
                    getUtilizationStatus(contract.utilization_percentage).color
                  }
                >
                  {getUtilizationStatus(contract.utilization_percentage).label}
                </span>
              </div>
              <Progress
                value={contract.utilization_percentage}
                className="h-3"
              />
            </div>

            {/* Dates & Terms */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg border">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Contract Period</span>
                </div>
                <div className="text-sm">
                  <div>
                    Start: {new Date(contract.start_date).toLocaleDateString()}
                  </div>
                  <div>
                    End: {new Date(contract.end_date).toLocaleDateString()}
                  </div>
                  <div
                    className={`mt-1 ${contract.days_until_expiry <= 30 ? "text-red-600" : contract.days_until_expiry <= 90 ? "text-amber-600" : "text-green-600"}`}
                  >
                    {formatDaysUntilExpiry(contract.days_until_expiry)}
                  </div>
                </div>
              </div>
              <div className="p-3 rounded-lg border">
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Supplier Info</span>
                </div>
                <div className="text-sm">
                  <div className="font-medium">{contract.supplier_name}</div>
                  {contract.categories && contract.categories.length > 0 && (
                    <div className="text-muted-foreground">
                      Categories: {contract.categories.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Category Breakdown */}
            {contract.category_breakdown &&
              contract.category_breakdown.length > 0 && (
                <div className="p-3 rounded-lg border">
                  <div className="text-sm font-medium mb-2">
                    Spend by Category
                  </div>
                  <div className="space-y-2">
                    {contract.category_breakdown.map((cat, index) => (
                      <div key={index} className="flex justify-between text-sm">
                        <span>{cat.category}</span>
                        <span className="font-medium">
                          {formatCurrency(cat.amount)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Monthly Spend */}
            {contract.monthly_spend && contract.monthly_spend.length > 0 && (
              <div className="p-3 rounded-lg border">
                <div className="text-sm font-medium mb-2">
                  Monthly Spend (Recent)
                </div>
                <div className="space-y-2">
                  {contract.monthly_spend.slice(-6).map((month, index) => (
                    <div key={index} className="flex justify-between text-sm">
                      <span>{month.month}</span>
                      <span className="font-medium">
                        {formatCurrency(month.amount)}
                      </span>
                    </div>
                  ))}
                </div>
                {contract.average_monthly_spend > 0 && (
                  <div className="mt-2 pt-2 border-t text-sm flex justify-between">
                    <span className="text-muted-foreground">
                      Monthly Average
                    </span>
                    <span className="font-medium">
                      {formatCurrency(contract.average_monthly_spend)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Auto-renew Badge */}
            {contract.auto_renew && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100">
                <RefreshCw className="h-4 w-4 text-blue-600" />
                <span className="text-sm text-blue-700">
                  This contract is set to auto-renew
                </span>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ContractsListSection() {
  const { data, isLoading } = useContracts();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedContractId, setSelectedContractId] = useState<number | null>(
    null,
  );

  const contracts = data?.contracts ?? [];
  const filteredContracts =
    statusFilter === "all"
      ? contracts
      : contracts.filter((c) => c.status === statusFilter);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Contracts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Contracts</CardTitle>
            <CardDescription>
              {contracts.length} total contracts
            </CardDescription>
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="expiring">Expiring Soon</SelectItem>
              <SelectItem value="expired">Expired</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {filteredContracts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No contracts found</p>
            <p className="text-sm mt-1">
              Contact your administrator to add contracts to your organization
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredContracts.map((contract) => {
              const statusDisplay = getContractStatusDisplay(contract.status);
              const utilizationStatus = getUtilizationStatus(
                contract.utilization_percentage,
              );

              return (
                <div
                  key={contract.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedContractId(contract.id)}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{contract.title}</span>
                      <Badge
                        variant="outline"
                        className={`${statusDisplay.color} ${statusDisplay.bgColor}`}
                      >
                        {statusDisplay.label}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <span>{contract.contract_number}</span>
                      <span className="mx-2">•</span>
                      <span>{contract.supplier_name}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">
                      {formatCurrency(contract.total_value)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatDaysUntilExpiry(contract.days_until_expiry)}
                    </div>
                  </div>
                  <div className="ml-4 w-24">
                    <div className="text-xs text-muted-foreground mb-1">
                      Utilization
                    </div>
                    <Progress
                      value={contract.utilization_percentage}
                      className="h-2"
                    />
                    <div className={`text-xs ${utilizationStatus.color}`}>
                      {contract.utilization_percentage.toFixed(0)}%
                    </div>
                  </div>
                  <div className="ml-4">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>

      {/* Contract Detail Modal */}
      <ContractDetailModal
        contractId={selectedContractId}
        isOpen={selectedContractId !== null}
        onClose={() => setSelectedContractId(null)}
      />
    </Card>
  );
}

function ExpiringContractsSection() {
  const [daysThreshold, setDaysThreshold] = useState(90);
  const { data, isLoading } = useExpiringContracts(daysThreshold);

  const contracts = data?.contracts ?? [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Expiring Contracts</CardTitle>
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Expiring Contracts
            </CardTitle>
            <CardDescription>Contracts requiring attention</CardDescription>
          </div>
          <Select
            value={String(daysThreshold)}
            onValueChange={(v) => setDaysThreshold(Number(v))}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="30">30 days</SelectItem>
              <SelectItem value="60">60 days</SelectItem>
              <SelectItem value="90">90 days</SelectItem>
              <SelectItem value="180">180 days</SelectItem>
              <SelectItem value="365">1 year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {contracts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="mx-auto h-12 w-12 mb-4 text-green-500" />
            <p>No contracts expiring within {daysThreshold} days</p>
          </div>
        ) : (
          <div className="space-y-4">
            {contracts.map((contract) => {
              const recDisplay = getRecommendationDisplay(
                contract.recommendation,
              );
              const RecommendationIcon =
                {
                  "check-circle": CheckCircle,
                  refresh: RefreshCw,
                  "x-circle": XCircle,
                  eye: Eye,
                }[recDisplay.icon] || Eye;

              return (
                <div
                  key={contract.id}
                  className="p-4 rounded-lg border bg-card"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="font-medium">{contract.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {contract.contract_number} • {contract.supplier_name}
                      </div>
                    </div>
                    <Badge
                      className={`${recDisplay.color} ${recDisplay.bgColor}`}
                    >
                      <RecommendationIcon className="h-3 w-3 mr-1" />
                      {recDisplay.label}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Value:</span>
                      <span className="ml-2 font-medium">
                        {formatCurrency(contract.total_value)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Spent:</span>
                      <span className="ml-2 font-medium">
                        {formatCurrency(contract.actual_spend)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        Utilization:
                      </span>
                      <span className="ml-2 font-medium">
                        {contract.utilization_percentage.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 text-sm">
                    <span
                      className={
                        contract.days_until_expiry <= 30
                          ? "text-red-600 font-medium"
                          : "text-amber-600"
                      }
                    >
                      <Calendar className="inline h-4 w-4 mr-1" />
                      {formatDaysUntilExpiry(contract.days_until_expiry)}
                    </span>
                    {contract.auto_renew && (
                      <Badge variant="outline" className="ml-2">
                        <RefreshCw className="h-3 w-3 mr-1" />
                        Auto-renew
                      </Badge>
                    )}
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    {contract.recommendation_reason}
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

function SavingsOpportunitiesSection() {
  const { data, isLoading } = useContractSavings();

  const opportunities = data?.opportunities ?? [];
  const totalSavings = data?.total_potential_savings ?? 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Savings Opportunities</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  const savingsByType = opportunities.reduce(
    (acc, opp) => {
      acc[opp.type] = (acc[opp.type] || 0) + opp.potential_savings;
      return acc;
    },
    {} as Record<string, number>,
  );

  const chartData = Object.entries(savingsByType).map(([type, value]) => ({
    name: getSavingsTypeDisplay(
      type as
        | "underutilized"
        | "off_contract"
        | "consolidation"
        | "price_variance",
    ).label,
    value,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PiggyBank className="h-5 w-5" />
          Savings Opportunities
        </CardTitle>
        <CardDescription>
          Total potential savings: {formatCurrency(totalSavings)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {opportunities.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <TrendingUp className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No savings opportunities identified</p>
            <p className="text-sm">Import more contract data for analysis</p>
          </div>
        ) : (
          <>
            {chartData.length > 0 && (
              <div className="h-48 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                    >
                      {chartData.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="space-y-4">
              {opportunities.slice(0, 5).map((opportunity, index) => {
                const typeDisplay = getSavingsTypeDisplay(opportunity.type);

                return (
                  <div key={index} className="p-4 rounded-lg border bg-card">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <Badge
                          className={`${typeDisplay.color} ${typeDisplay.bgColor} mb-1`}
                        >
                          {typeDisplay.label}
                        </Badge>
                        <div className="font-medium">{opportunity.title}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-green-600">
                          {formatCurrency(opportunity.potential_savings)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {(opportunity.confidence * 100).toFixed(0)}%
                          confidence
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {opportunity.description}
                    </p>
                    <div className="text-sm">
                      <span className="font-medium">Action: </span>
                      {opportunity.recommended_action}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function RenewalRecommendationsSection() {
  const { data, isLoading } = useContractRenewals();

  const recommendations = data?.recommendations ?? [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Renewal Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const sortedRecommendations = [...recommendations].sort(
    (a, b) => priorityOrder[a.priority] - priorityOrder[b.priority],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5" />
          Renewal Recommendations
        </CardTitle>
        <CardDescription>
          {recommendations.length} contracts with recommendations
        </CardDescription>
      </CardHeader>
      <CardContent>
        {sortedRecommendations.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No renewal recommendations at this time</p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedRecommendations.map((rec) => {
              const recDisplay = getRecommendationDisplay(rec.recommendation);
              const priorityColors = {
                high: "border-l-red-500",
                medium: "border-l-amber-500",
                low: "border-l-blue-500",
              };

              return (
                <div
                  key={rec.contract_id}
                  className={`p-3 rounded-lg border-l-4 ${priorityColors[rec.priority]} bg-card`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{rec.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {rec.supplier_name} • Expires:{" "}
                        {new Date(rec.end_date).toLocaleDateString()}
                      </div>
                    </div>
                    <Badge
                      className={`${recDisplay.color} ${recDisplay.bgColor}`}
                    >
                      {recDisplay.label}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm">
                    <span className="text-muted-foreground">
                      {rec.recommendation_reason}
                    </span>
                    {rec.suggested_new_value && (
                      <span className="ml-2 text-green-600 font-medium">
                        Suggested value:{" "}
                        {formatCurrency(rec.suggested_new_value)}
                      </span>
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

function ContractVsActualSection() {
  const { data, isLoading } = useContractVsActual();

  const contracts = data?.contracts ?? [];
  const summary = data?.summary;
  const monthlyComparison = data?.monthly_comparison ?? [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Contract vs Actual Spend</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  const chartData = contracts.slice(0, 10).map((c) => ({
    name: c.title.length > 20 ? c.title.substring(0, 20) + "..." : c.title,
    contracted: c.contracted_value,
    actual: c.actual_spend,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Contract vs Actual Spend
        </CardTitle>
        {summary && (
          <CardDescription>
            Overall utilization: {summary.overall_utilization.toFixed(1)}%
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        {contracts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <BarChart3 className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No contract data available</p>
          </div>
        ) : (
          <>
            {summary && (
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-sm text-muted-foreground">
                    Contracted
                  </div>
                  <div className="text-lg font-bold">
                    {formatCurrency(summary.total_contracted)}
                  </div>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-sm text-muted-foreground">Actual</div>
                  <div className="text-lg font-bold">
                    {formatCurrency(summary.total_actual)}
                  </div>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted">
                  <div className="text-sm text-muted-foreground">Variance</div>
                  <div
                    className={`text-lg font-bold ${summary.total_variance >= 0 ? "text-green-600" : "text-red-600"}`}
                  >
                    {formatCurrency(Math.abs(summary.total_variance))}
                    <span className="text-sm ml-1">
                      {summary.total_variance >= 0 ? "under" : "over"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <YAxis type="category" dataKey="name" width={100} />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                  />
                  <Legend />
                  <Bar dataKey="contracted" name="Contracted" fill="#3b82f6" />
                  <Bar dataKey="actual" name="Actual" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {monthlyComparison.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium mb-3">Monthly Trend</h4>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyComparison}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis tickFormatter={(value) => formatCurrency(value)} />
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="contracted"
                        name="Contracted"
                        stroke="#3b82f6"
                      />
                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="Actual"
                        stroke="#22c55e"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function ContractsPage() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <FileText className="h-8 w-8 text-blue-600" />
          Contract Optimization
        </h1>
        <p className="text-muted-foreground mt-1">
          Analyze contract performance, track renewals, and identify savings
          opportunities
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
            <Building2 className="h-4 w-4 mr-2" />
            Contracts
          </TabsTrigger>
          <TabsTrigger value="expiring">
            <Clock className="h-4 w-4 mr-2" />
            Expiring
          </TabsTrigger>
          <TabsTrigger value="savings">
            <PiggyBank className="h-4 w-4 mr-2" />
            Savings
          </TabsTrigger>
          <TabsTrigger value="renewals">
            <RefreshCw className="h-4 w-4 mr-2" />
            Renewals
          </TabsTrigger>
          <TabsTrigger value="comparison">
            <BarChart3 className="h-4 w-4 mr-2" />
            Comparison
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <ContractsListSection />
        </TabsContent>

        <TabsContent value="expiring">
          <ExpiringContractsSection />
        </TabsContent>

        <TabsContent value="savings">
          <SavingsOpportunitiesSection />
        </TabsContent>

        <TabsContent value="renewals">
          <RenewalRecommendationsSection />
        </TabsContent>

        <TabsContent value="comparison">
          <ContractVsActualSection />
        </TabsContent>
      </Tabs>
    </div>
  );
}
