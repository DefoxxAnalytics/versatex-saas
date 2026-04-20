/**
 * DrillDownModal Component
 *
 * A modal that shows detailed breakdown when users click on chart segments.
 * Displays transaction list, sub-breakdown, and key metrics for the selected entity.
 */

import { useMemo } from "react";
import {
  X,
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingCart,
  Building2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Chart } from "./Chart";
import type { ProcurementRecord } from "@/hooks/useProcurementData";

interface DrillDownModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal closes */
  onClose: () => void;
  /** Title for the modal */
  title: string;
  /** Type of entity being drilled down */
  entityType: "category" | "supplier" | "location" | "year";
  /** Name of the entity (e.g., category name, supplier name) */
  entityName: string;
  /** Filtered data for this entity */
  data: ProcurementRecord[];
  /** Total spend for percentage calculations */
  totalSpend?: number;
}

/**
 * Format currency value
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format date for display
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function DrillDownModal({
  open,
  onClose,
  title,
  entityType,
  entityName,
  data,
  totalSpend = 0,
}: DrillDownModalProps) {
  // Calculate metrics for the selected entity
  const metrics = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        totalSpend: 0,
        transactionCount: 0,
        avgTransaction: 0,
        percentage: 0,
        uniqueSuppliers: 0,
        uniqueCategories: 0,
      };
    }

    const entitySpend = data.reduce((sum, r) => sum + r.amount, 0);
    const avgTransaction = entitySpend / data.length;
    const percentage = totalSpend > 0 ? (entitySpend / totalSpend) * 100 : 0;
    const uniqueSuppliers = new Set(data.map((r) => r.supplier)).size;
    const uniqueCategories = new Set(data.map((r) => r.category)).size;

    return {
      totalSpend: entitySpend,
      transactionCount: data.length,
      avgTransaction,
      percentage,
      uniqueSuppliers,
      uniqueCategories,
    };
  }, [data, totalSpend]);

  // Get sub-breakdown based on entity type
  const subBreakdown = useMemo(() => {
    if (!data || data.length === 0) return [];

    // If looking at a category, break down by supplier
    // If looking at a supplier, break down by category
    const breakdownField = entityType === "supplier" ? "category" : "supplier";

    const breakdown = new Map<string, { spend: number; count: number }>();

    data.forEach((record) => {
      const key = record[breakdownField] || "Unknown";
      const current = breakdown.get(key) || { spend: 0, count: 0 };
      breakdown.set(key, {
        spend: current.spend + record.amount,
        count: current.count + 1,
      });
    });

    return Array.from(breakdown.entries())
      .map(([name, { spend, count }]) => ({
        name,
        spend,
        count,
        percentage:
          metrics.totalSpend > 0 ? (spend / metrics.totalSpend) * 100 : 0,
      }))
      .sort((a, b) => b.spend - a.spend)
      .slice(0, 10); // Top 10
  }, [data, entityType, metrics.totalSpend]);

  // Generate pie chart config for sub-breakdown
  const pieChartConfig = useMemo(() => {
    return {
      tooltip: {
        trigger: "item" as const,
        formatter: "{b}: {c} ({d}%)",
      },
      series: [
        {
          type: "pie" as const,
          radius: ["40%", "70%"],
          data: subBreakdown.map((item) => ({
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
          label: {
            show: false,
          },
        },
      ],
    };
  }, [subBreakdown]);

  // Get recent transactions (last 10)
  const recentTransactions = useMemo(() => {
    if (!data || data.length === 0) return [];
    return [...data]
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, 10);
  }, [data]);

  const getEntityIcon = () => {
    switch (entityType) {
      case "category":
        return <ShoppingCart className="h-5 w-5" />;
      case "supplier":
        return <Building2 className="h-5 w-5" />;
      default:
        return <DollarSign className="h-5 w-5" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            {getEntityIcon()}
            {title}: {entityName}
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="h-[calc(90vh-120px)] pr-4">
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">
                    Total Spend
                  </div>
                  <div className="text-2xl font-bold">
                    {formatCurrency(metrics.totalSpend)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {metrics.percentage.toFixed(1)}% of total
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">
                    Transactions
                  </div>
                  <div className="text-2xl font-bold">
                    {metrics.transactionCount.toLocaleString()}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">
                    Avg Transaction
                  </div>
                  <div className="text-2xl font-bold">
                    {formatCurrency(metrics.avgTransaction)}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="text-sm text-muted-foreground">
                    {entityType === "supplier" ? "Categories" : "Suppliers"}
                  </div>
                  <div className="text-2xl font-bold">
                    {entityType === "supplier"
                      ? metrics.uniqueCategories
                      : metrics.uniqueSuppliers}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sub-breakdown */}
            {subBreakdown.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pie Chart */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">
                      Breakdown by{" "}
                      {entityType === "supplier" ? "Category" : "Supplier"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Chart
                      title=""
                      option={pieChartConfig}
                      height={250}
                      className="border-0 shadow-none"
                    />
                  </CardContent>
                </Card>

                {/* List */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">
                      Top{" "}
                      {entityType === "supplier" ? "Categories" : "Suppliers"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {subBreakdown.map((item, index) => (
                        <div
                          key={item.name}
                          className="flex items-center justify-between py-2 border-b last:border-0"
                        >
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className="w-6 h-6 justify-center p-0"
                            >
                              {index + 1}
                            </Badge>
                            <span
                              className="text-sm truncate max-w-[150px]"
                              title={item.name}
                            >
                              {item.name}
                            </span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium">
                              {formatCurrency(item.spend)}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {item.percentage.toFixed(1)}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Recent Transactions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Recent Transactions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {recentTransactions.map((tx, index) => (
                    <div
                      key={`${tx.date}-${tx.supplier}-${index}`}
                      className="flex items-center justify-between py-2 border-b last:border-0"
                    >
                      <div>
                        <div className="text-sm font-medium">
                          {entityType === "supplier"
                            ? tx.category
                            : tx.supplier}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDate(tx.date)} •{" "}
                          {tx.subcategory || "No subcategory"}
                        </div>
                      </div>
                      <div className="text-sm font-medium">
                        {formatCurrency(tx.amount)}
                      </div>
                    </div>
                  ))}
                  {recentTransactions.length === 0 && (
                    <div className="text-center py-4 text-muted-foreground">
                      No transactions found
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
