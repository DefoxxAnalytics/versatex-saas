/**
 * Overview Page Component
 *
 * Main dashboard view showing key procurement metrics and statistics.
 *
 * Features:
 * - Summary statistics cards (total spend, suppliers, categories, avg transaction)
 * - Four interactive charts (category, trend, suppliers, distribution)
 * - Real-time data from TanStack Query via backend analytics API
 * - Responsive grid layout
 * - Loading and empty states
 * - Server-side drill-down modals for accurate data
 *
 * Security:
 * - All data validated before display
 * - No XSS vulnerabilities
 *
 * Performance:
 * - Server-side aggregations (no client-side data truncation)
 * - Lazy-loaded ECharts
 */

import { useState, useMemo } from "react";
import {
  DollarSign,
  Users,
  Package,
  TrendingUp,
  ExternalLink,
  ShoppingCart,
  Building2,
  Loader2,
} from "lucide-react";
import {
  useFilteredProcurementData,
} from "@/hooks/useProcurementData";
import {
  useOverviewStats,
  useSpendByCategory,
  useSpendBySupplier,
  useMonthlyTrend,
  useCategoryDrilldown,
  useSupplierDrilldown,
} from "@/hooks/useAnalytics";
import { usePermissions } from "@/contexts/PermissionContext";
import { StatCard } from "@/components/StatCard";
import { Chart } from "@/components/Chart";
import { SkeletonCard } from "@/components/SkeletonCard";
import { SkeletonChart } from "@/components/SkeletonChart";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getCategoryChartFromAPI,
  getTrendChartFromAPI,
  getSupplierChartFromAPI,
  getSpendDistributionConfig,
} from "@/lib/chartConfigs";
import type { CategoryDrilldown, SupplierDrilldown } from "@/lib/api";

interface SelectedEntity {
  type: "category" | "supplier";
  id: number;
  name: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface CategoryDrilldownModalProps {
  open: boolean;
  onClose: () => void;
  data: CategoryDrilldown | null;
  isLoading: boolean;
  totalSpend: number;
}

function CategoryDrilldownModal({
  open,
  onClose,
  data,
  isLoading,
  totalSpend,
}: CategoryDrilldownModalProps) {
  const pieChartConfig = useMemo(() => {
    if (!data?.suppliers?.length) return null;
    return {
      tooltip: {
        trigger: "item" as const,
        formatter: "{b}: {c} ({d}%)",
      },
      legend: { show: false },
      series: [
        {
          type: "pie" as const,
          radius: ["40%", "70%"],
          center: ["50%", "50%"],
          data: data.suppliers.map((item) => ({
            name: item.name,
            value: Math.round(item.spend),
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.5)",
            },
          },
          label: { show: false },
        },
      ],
    };
  }, [data?.suppliers]);

  const percentage = totalSpend > 0 && data
    ? (data.total_spend / totalSpend) * 100
    : 0;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="lg" className="max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <ShoppingCart className="h-5 w-5" />
            Category: {data?.category_name || "Loading..."}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !data ? (
          <div className="text-center py-8 text-muted-foreground">
            No data available
          </div>
        ) : (
          <ScrollArea className="h-[calc(90vh-120px)] pr-4">
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Total Spend</div>
                    <div className="text-2xl font-bold">{formatCurrency(data.total_spend)}</div>
                    <div className="text-xs text-muted-foreground">{percentage.toFixed(1)}% of total</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Transactions</div>
                    <div className="text-2xl font-bold">{data.transaction_count.toLocaleString()}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Avg Transaction</div>
                    <div className="text-2xl font-bold">{formatCurrency(data.avg_transaction)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Suppliers</div>
                    <div className="text-2xl font-bold">{data.supplier_count}</div>
                  </CardContent>
                </Card>
              </div>

              {data.suppliers.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Breakdown by Supplier</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {pieChartConfig && (
                        <Chart title="" option={pieChartConfig} height={250} className="border-0 shadow-none" />
                      )}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Top Suppliers</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {data.suppliers.map((item, index) => (
                          <div key={item.id} className="flex items-center justify-between py-2 border-b last:border-0">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="w-6 h-6 justify-center p-0">{index + 1}</Badge>
                              <span className="text-sm truncate max-w-[150px]" title={item.name}>{item.name}</span>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium">{formatCurrency(item.spend)}</div>
                              <div className="text-xs text-muted-foreground">{item.percent_of_total.toFixed(1)}%</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Recent Transactions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {data.recent_transactions.map((tx) => (
                      <div key={tx.id} className="flex items-center justify-between py-2 border-b last:border-0">
                        <div>
                          <div className="text-sm font-medium">{tx.supplier_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(tx.date)} {tx.description && `• ${tx.description}`}
                          </div>
                        </div>
                        <div className="text-sm font-medium">{formatCurrency(tx.amount)}</div>
                      </div>
                    ))}
                    {data.recent_transactions.length === 0 && (
                      <div className="text-center py-4 text-muted-foreground">No transactions found</div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface SupplierDrilldownModalProps {
  open: boolean;
  onClose: () => void;
  data: SupplierDrilldown | null;
  isLoading: boolean;
  totalSpend: number;
}

function SupplierDrilldownModal({
  open,
  onClose,
  data,
  isLoading,
  totalSpend,
}: SupplierDrilldownModalProps) {
  const pieChartConfig = useMemo(() => {
    if (!data?.categories?.length) return null;
    return {
      tooltip: {
        trigger: "item" as const,
        formatter: "{b}: {c} ({d}%)",
      },
      legend: { show: false },
      series: [
        {
          type: "pie" as const,
          radius: ["40%", "70%"],
          center: ["50%", "50%"],
          data: data.categories.map((item) => ({
            name: item.name,
            value: Math.round(item.spend),
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: "rgba(0, 0, 0, 0.5)",
            },
          },
          label: { show: false },
        },
      ],
    };
  }, [data?.categories]);

  const percentage = totalSpend > 0 && data
    ? (data.total_spend / totalSpend) * 100
    : 0;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="lg" className="max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Building2 className="h-5 w-5" />
            Supplier: {data?.supplier_name || "Loading..."}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !data ? (
          <div className="text-center py-8 text-muted-foreground">
            No data available
          </div>
        ) : (
          <ScrollArea className="h-[calc(90vh-120px)] pr-4">
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Total Spend</div>
                    <div className="text-2xl font-bold">{formatCurrency(data.total_spend)}</div>
                    <div className="text-xs text-muted-foreground">{percentage.toFixed(1)}% of total</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Transactions</div>
                    <div className="text-2xl font-bold">{data.transaction_count.toLocaleString()}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Avg Transaction</div>
                    <div className="text-2xl font-bold">{formatCurrency(data.avg_transaction)}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-sm text-muted-foreground">Categories</div>
                    <div className="text-2xl font-bold">{data.categories.length}</div>
                  </CardContent>
                </Card>
              </div>

              {data.categories.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Breakdown by Category</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {pieChartConfig && (
                        <Chart title="" option={pieChartConfig} height={250} className="border-0 shadow-none" />
                      )}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Top Categories</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {data.categories.map((item, index) => (
                          <div key={item.name} className="flex items-center justify-between py-2 border-b last:border-0">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="w-6 h-6 justify-center p-0">{index + 1}</Badge>
                              <span className="text-sm truncate max-w-[150px]" title={item.name}>{item.name}</span>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-medium">{formatCurrency(item.spend)}</div>
                              <div className="text-xs text-muted-foreground">{item.percent_of_total.toFixed(1)}%</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {data.subcategories && data.subcategories.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Subcategories</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {data.subcategories.slice(0, 10).map((item, index) => (
                        <div key={item.name} className="flex items-center justify-between py-2 border-b last:border-0">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="w-6 h-6 justify-center p-0">{index + 1}</Badge>
                            <span className="text-sm truncate max-w-[200px]" title={item.name}>{item.name}</span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium">{formatCurrency(item.spend)}</div>
                            <div className="text-xs text-muted-foreground">{item.percent_of_total.toFixed(1)}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function Overview() {
  const { data: overviewStats, isLoading: statsLoading } = useOverviewStats();
  const { data: categoryData = [], isLoading: categoryLoading } = useSpendByCategory();
  const { data: supplierData = [], isLoading: supplierLoading } = useSpendBySupplier();
  const { data: trendData = [], isLoading: trendLoading } = useMonthlyTrend(12);
  const { data: filteredData = [] } = useFilteredProcurementData();

  const { hasPermission } = usePermissions();
  const canAccessAdmin = hasPermission("admin_panel");

  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);

  const { data: categoryDrilldownData, isLoading: categoryDrilldownLoading } = useCategoryDrilldown(
    selectedEntity?.type === "category" ? selectedEntity.id : null
  );

  const { data: supplierDrilldownData, isLoading: supplierDrilldownLoading } = useSupplierDrilldown(
    selectedEntity?.type === "supplier" ? selectedEntity.id : null
  );

  const isLoading = statsLoading || categoryLoading || supplierLoading || trendLoading;
  const adminUploadUrl = `${window.location.protocol}//${window.location.hostname}:8001/admin/procurement/dataupload/upload-csv/`;

  const totalSpend = overviewStats?.total_spend ?? 0;
  const supplierCount = overviewStats?.supplier_count ?? 0;
  const categoryCount = overviewStats?.category_count ?? 0;
  const avgTransaction = overviewStats?.avg_transaction ?? 0;

  const handleCategoryClick = (params: { name: string; value: number }) => {
    const category = categoryData.find((c) => c.category === params.name);
    if (category?.category_id) {
      setSelectedEntity({
        type: "category",
        id: category.category_id,
        name: params.name,
      });
    }
  };

  const handleSupplierClick = (params: { name: string; value: number }) => {
    const supplier = supplierData.find((s) => s.supplier === params.name);
    if (supplier?.supplier_id) {
      setSelectedEntity({
        type: "supplier",
        id: supplier.supplier_id,
        name: params.name,
      });
    }
  };

  const closeModal = () => {
    setSelectedEntity(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Overview</h1>
          <p className="text-gray-600 mt-2">Key metrics and insights from your procurement data</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart height={350} type="bar" />
          <SkeletonChart height={350} type="line" />
          <SkeletonChart height={350} type="bar" />
          <SkeletonChart height={350} type="pie" />
        </div>
      </div>
    );
  }

  const hasNoData = overviewStats !== undefined && overviewStats.transaction_count === 0;
  if (hasNoData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md">
          <Package className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Data Available</h2>
          <p className="text-gray-600 mb-6">
            {canAccessAdmin
              ? "Upload your procurement data via the Admin Panel to see analytics and insights."
              : "Contact an administrator to upload procurement data to see analytics and insights."}
          </p>
          {canAccessAdmin && (
            <a
              href={adminUploadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              Go to Admin Panel
            </a>
          )}
        </div>
      </div>
    );
  }

  const spendByCategoryConfig = getCategoryChartFromAPI(categoryData);
  const spendTrendConfig = getTrendChartFromAPI(trendData);
  const topSuppliersConfig = getSupplierChartFromAPI(supplierData);
  const spendDistributionConfig = getSpendDistributionConfig(filteredData);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Overview</h1>
        <p className="text-gray-600 mt-2">Key metrics and insights from your procurement data</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard title="Total Spend" value={formatCurrency(totalSpend)} description="Across all categories" icon={DollarSign} />
        <StatCard title="Suppliers" value={supplierCount} description="Unique vendors" icon={Users} />
        <StatCard title="Categories" value={categoryCount} description="Spend categories" icon={Package} />
        <StatCard title="Avg Transaction" value={formatCurrency(avgTransaction)} description="Per purchase" icon={TrendingUp} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Chart
          title="Spend by Category"
          description="Shows how your procurement budget is distributed across different categories. Click a category to see details."
          option={spendByCategoryConfig}
          height={350}
          loading={isLoading}
          onChartClick={handleCategoryClick}
        />
        <Chart
          title="Spend Trend Over Time"
          description="Track monthly spending patterns to identify trends, seasonal variations, and anomalies in your procurement activity."
          option={spendTrendConfig}
          height={350}
          loading={isLoading}
        />
        <Chart
          title="Top 10 Suppliers"
          description="Your largest vendors by total spend. Click a supplier to see details."
          option={topSuppliersConfig}
          height={350}
          loading={isLoading}
          onChartClick={handleSupplierClick}
        />
        <Chart
          title="Spend Distribution"
          description="Categorizes transactions into High (top 20%), Medium (next 30%), and Low (bottom 50%) value tiers. Helps identify spend concentration and tail spend opportunities."
          option={spendDistributionConfig}
          height={350}
          loading={isLoading}
        />
      </div>

      <CategoryDrilldownModal
        open={selectedEntity?.type === "category"}
        onClose={closeModal}
        data={categoryDrilldownData ?? null}
        isLoading={categoryDrilldownLoading}
        totalSpend={totalSpend}
      />

      <SupplierDrilldownModal
        open={selectedEntity?.type === "supplier"}
        onClose={closeModal}
        data={supplierDrilldownData ?? null}
        isLoading={supplierDrilldownLoading}
        totalSpend={totalSpend}
      />
    </div>
  );
}
