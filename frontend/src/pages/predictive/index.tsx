/**
 * Predictive Analytics Page
 *
 * Displays spending forecasts and trend predictions:
 * - Overall spending forecast with confidence intervals
 * - Trend analysis across categories and suppliers
 * - Budget projection and variance analysis
 * - Growth metrics
 */

import { useState, useMemo } from "react";
import {
  LineChart,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  DollarSign,
  Target,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Info,
  HelpCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { StatCard } from "@/components/StatCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import {
  AreaChart,
  Area,
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import {
  useSpendingForecast,
  useTrendAnalysis,
  getTrendDisplay,
  formatChangeRate,
} from "@/hooks/usePredictions";
import type { ForecastPoint, TrendDirection } from "@/lib/api";

// Trend indicator component
function TrendIndicator({
  direction,
  rate,
}: {
  direction: TrendDirection;
  rate: number;
}) {
  const display = getTrendDisplay(direction);
  const Icon =
    direction === "increasing"
      ? TrendingUp
      : direction === "decreasing"
        ? TrendingDown
        : Minus;

  return (
    <div className={`flex items-center gap-1 ${display.color}`}>
      <Icon className="h-4 w-4" />
      <span className="text-sm font-medium">
        {display.label} ({formatChangeRate(rate)})
      </span>
    </div>
  );
}

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// Custom tooltip for forecast chart
function ForecastTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload as ForecastPoint;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4">
      <p className="font-semibold text-gray-900 mb-2">{label}</p>
      <div className="space-y-1 text-sm">
        <p className="text-blue-600">
          Predicted: {formatCurrency(data.predicted_spend)}
        </p>
        <p className="text-gray-600">
          80% Range: {formatCurrency(data.lower_bound_80)} -{" "}
          {formatCurrency(data.upper_bound_80)}
        </p>
        <p className="text-gray-500 text-xs">
          95% Range: {formatCurrency(data.lower_bound_95)} -{" "}
          {formatCurrency(data.upper_bound_95)}
        </p>
      </div>
    </div>
  );
}

export default function PredictivePage() {
  const [forecastMonths, setForecastMonths] = useState(6);
  const {
    data: forecastData,
    isLoading: forecastLoading,
    error: forecastError,
    refetch: refetchForecast,
    isFetching: forecastFetching,
  } = useSpendingForecast(forecastMonths);

  const {
    data: trendData,
    isLoading: trendLoading,
    error: trendError,
  } = useTrendAnalysis();

  const isLoading = forecastLoading || trendLoading;
  const hasError = forecastError || trendError;

  // Prepare chart data with month labels
  const chartData = useMemo(() => {
    if (!forecastData?.forecast) return [];
    return forecastData.forecast.map((f) => ({
      ...f,
      month: f.month.slice(0, 7), // Format as YYYY-MM
    }));
  }, [forecastData]);

  // Calculate summary values
  const summary = useMemo(() => {
    if (!forecastData?.forecast || forecastData.forecast.length === 0) {
      return {
        nextMonth: 0,
        nextQuarter: 0,
        forecastTotal: 0,
      };
    }

    const forecast = forecastData.forecast;
    return {
      nextMonth: forecast[0]?.predicted_spend || 0,
      nextQuarter: forecast
        .slice(0, 3)
        .reduce((sum, f) => sum + f.predicted_spend, 0),
      forecastTotal: forecast.reduce((sum, f) => sum + f.predicted_spend, 0),
    };
  }, [forecastData]);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-8 p-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <LineChart className="h-8 w-8 text-teal-600" />
            Predictive Analytics
          </h1>
          <p className="text-gray-600 mt-2">
            Forecast future spending and identify trends
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>

        <Card className="animate-pulse">
          <CardContent className="pt-6">
            <div className="h-80 bg-gray-200 rounded" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (hasError) {
    return (
      <div className="space-y-8 p-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <LineChart className="h-8 w-8 text-teal-600" />
            Predictive Analytics
          </h1>
        </div>

        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center max-w-md">
            <Info className="h-16 w-16 text-yellow-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Unable to Generate Predictions
            </h2>
            <p className="text-gray-600 mb-6">
              There may be insufficient historical data to generate forecasts.
              Upload more transaction data to enable predictive analytics.
            </p>
            <Button onClick={() => refetchForecast()} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // No data state
  if (!forecastData || forecastData.forecast.length === 0) {
    return (
      <div className="space-y-8 p-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <LineChart className="h-8 w-8 text-teal-600" />
            Predictive Analytics
          </h1>
        </div>

        <div className="flex items-center justify-center min-h-[300px]">
          <div className="text-center max-w-md">
            <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Not Enough Data
            </h2>
            <p className="text-gray-600">
              Predictive analytics requires historical spending data. Upload
              procurement transactions to generate forecasts.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const { trend, model_accuracy } = forecastData;

  return (
    <div className="space-y-8 p-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <LineChart className="h-8 w-8 text-teal-600" />
            Predictive Analytics
          </h1>
          <p className="text-gray-600 mt-2">
            Forecast future spending and identify trends
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={forecastMonths}
            onChange={(e) => setForecastMonths(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value={3}>3 months</option>
            <option value={6}>6 months</option>
            <option value={12}>12 months</option>
            <option value={24}>24 months</option>
          </select>
          <Button
            onClick={() => refetchForecast()}
            variant="outline"
            disabled={forecastFetching}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${forecastFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatCard
          title="Next Month"
          value={formatCurrency(summary.nextMonth)}
          description="Predicted spend"
          icon={Calendar}
        />
        <StatCard
          title="Next Quarter"
          value={formatCurrency(summary.nextQuarter)}
          description="3-month forecast"
          icon={Target}
        />
        <StatCard
          title={`${forecastMonths}-Month Total`}
          value={formatCurrency(summary.forecastTotal)}
          description="Forecast period total"
          icon={DollarSign}
        />
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Overall Trend
            </CardTitle>
            <TrendingUp className="h-5 w-5 text-gray-400" />
          </CardHeader>
          <CardContent>
            <TrendIndicator
              direction={trend.direction}
              rate={trend.monthly_change_rate}
            />
            {trend.seasonality_detected && (
              <p className="text-xs text-gray-500 mt-2">Seasonality detected</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Forecast Chart */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-teal-600" />
                Spending Forecast
              </CardTitle>
              <CardDescription>
                Predicted spending with confidence intervals
              </CardDescription>
            </div>
            {model_accuracy.mape && (
              <TooltipProvider>
                <UITooltip>
                  <TooltipTrigger>
                    <Badge variant="outline" className="text-xs cursor-help">
                      Model Accuracy: {(100 - model_accuracy.mape).toFixed(0)}%
                      <HelpCircle className="h-3 w-3 ml-1 inline" />
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <p>
                      Based on MAPE of {model_accuracy.mape}%. A{" "}
                      {(100 - model_accuracy.mape).toFixed(0)}% accuracy means
                      predictions are typically within {model_accuracy.mape}% of
                      actual values.
                    </p>
                  </TooltipContent>
                </UITooltip>
              </TooltipProvider>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#6b7280" />
              <YAxis
                tick={{ fontSize: 12 }}
                stroke="#6b7280"
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
              />
              <Tooltip content={<ForecastTooltip />} />
              <Legend />
              {/* 95% Confidence Interval */}
              <Area
                type="monotone"
                dataKey="upper_bound_95"
                stackId="1"
                stroke="transparent"
                fill="#e0f2fe"
                name="95% Upper"
              />
              <Area
                type="monotone"
                dataKey="lower_bound_95"
                stackId="2"
                stroke="transparent"
                fill="white"
                name="95% Lower"
              />
              {/* 80% Confidence Interval */}
              <Area
                type="monotone"
                dataKey="upper_bound_80"
                stroke="transparent"
                fill="#bae6fd"
                fillOpacity={0.5}
                name="80% Upper"
              />
              <Area
                type="monotone"
                dataKey="lower_bound_80"
                stroke="transparent"
                fill="white"
                fillOpacity={0.5}
                name="80% Lower"
              />
              {/* Predicted Line */}
              <Line
                type="monotone"
                dataKey="predicted_spend"
                stroke="#0ea5e9"
                strokeWidth={3}
                dot={{ fill: "#0ea5e9", strokeWidth: 2 }}
                name="Predicted Spend"
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* Peak Months */}
          {trend.peak_months && trend.peak_months.length > 0 && (
            <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-100">
              <p className="text-sm text-amber-800">
                <strong>Peak Spending Months:</strong>{" "}
                {trend.peak_months.join(", ")}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trend Analysis Section */}
      {trendData && (
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-purple-600" />
              Trend Analysis
            </CardTitle>
            <CardDescription>
              Spending trends across categories and suppliers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="growth">
              <TabsList className="mb-6">
                <TabsTrigger value="growth">Growth Metrics</TabsTrigger>
                <TabsTrigger value="categories">Category Trends</TabsTrigger>
                <TabsTrigger value="suppliers">Supplier Trends</TabsTrigger>
              </TabsList>

              <TabsContent value="growth">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {trendData.growth_metrics.three_month_growth !==
                    undefined && (
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">
                            3-Month Growth
                          </span>
                          {trendData.growth_metrics.three_month_growth >= 0 ? (
                            <ArrowUpRight className="h-5 w-5 text-red-500" />
                          ) : (
                            <ArrowDownRight className="h-5 w-5 text-green-500" />
                          )}
                        </div>
                        <p
                          className={`text-2xl font-bold mt-2 ${
                            trendData.growth_metrics.three_month_growth >= 0
                              ? "text-red-600"
                              : "text-green-600"
                          }`}
                        >
                          {trendData.growth_metrics.three_month_growth >= 0
                            ? "+"
                            : ""}
                          {trendData.growth_metrics.three_month_growth.toFixed(
                            1,
                          )}
                          %
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  {trendData.growth_metrics.six_month_growth !== undefined && (
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">
                            6-Month Growth
                          </span>
                          {trendData.growth_metrics.six_month_growth >= 0 ? (
                            <ArrowUpRight className="h-5 w-5 text-red-500" />
                          ) : (
                            <ArrowDownRight className="h-5 w-5 text-green-500" />
                          )}
                        </div>
                        <p
                          className={`text-2xl font-bold mt-2 ${
                            trendData.growth_metrics.six_month_growth >= 0
                              ? "text-red-600"
                              : "text-green-600"
                          }`}
                        >
                          {trendData.growth_metrics.six_month_growth >= 0
                            ? "+"
                            : ""}
                          {trendData.growth_metrics.six_month_growth.toFixed(1)}
                          %
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  {trendData.growth_metrics.yoy_growth !== undefined && (
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">
                            Year-over-Year
                          </span>
                          {trendData.growth_metrics.yoy_growth >= 0 ? (
                            <ArrowUpRight className="h-5 w-5 text-red-500" />
                          ) : (
                            <ArrowDownRight className="h-5 w-5 text-green-500" />
                          )}
                        </div>
                        <p
                          className={`text-2xl font-bold mt-2 ${
                            trendData.growth_metrics.yoy_growth >= 0
                              ? "text-red-600"
                              : "text-green-600"
                          }`}
                        >
                          {trendData.growth_metrics.yoy_growth >= 0 ? "+" : ""}
                          {trendData.growth_metrics.yoy_growth.toFixed(1)}%
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="categories">
                {trendData.category_trends.length > 0 ? (
                  <div className="space-y-3">
                    {trendData.category_trends.map((cat) => {
                      const display = getTrendDisplay(cat.direction);
                      return (
                        <div
                          key={cat.category_id}
                          className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium text-gray-900">
                            {cat.category_name}
                          </span>
                          <div className="flex items-center gap-3">
                            <Badge
                              className={`${display.bgColor} ${display.color} border-0`}
                            >
                              {display.label}
                            </Badge>
                            <span
                              className={`text-sm font-medium ${display.color}`}
                            >
                              {formatChangeRate(cat.change_rate)}/month
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">
                    Not enough data to show category trends
                  </p>
                )}
              </TabsContent>

              <TabsContent value="suppliers">
                {trendData.supplier_trends.length > 0 ? (
                  <div className="space-y-3">
                    {trendData.supplier_trends.map((sup) => {
                      const display = getTrendDisplay(sup.direction);
                      return (
                        <div
                          key={sup.supplier_id}
                          className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium text-gray-900">
                            {sup.supplier_name}
                          </span>
                          <div className="flex items-center gap-3">
                            <Badge
                              className={`${display.bgColor} ${display.color} border-0`}
                            >
                              {display.label}
                            </Badge>
                            <span
                              className={`text-sm font-medium ${display.color}`}
                            >
                              {formatChangeRate(sup.change_rate)}/month
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-8">
                    Not enough data to show supplier trends
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Model Info */}
      <TooltipProvider>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Info className="h-4 w-4" />
              Model Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">Data Points Used</span>
                  <UITooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-3 w-3 text-gray-400" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>
                        The number of historical months used to train the
                        prediction model. More data points generally improve
                        accuracy.
                      </p>
                    </TooltipContent>
                  </UITooltip>
                </div>
                <p className="font-medium">
                  {model_accuracy.data_points_used} months
                </p>
              </div>
              {model_accuracy.mape && (
                <div>
                  <div className="flex items-center gap-1">
                    <span className="text-gray-500">Forecast Error (MAPE)</span>
                    <UITooltip>
                      <TooltipTrigger>
                        <HelpCircle className="h-3 w-3 text-gray-400" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>
                          <strong>Mean Absolute Percentage Error</strong>
                        </p>
                        <p className="mt-1">
                          Measures average prediction error as a percentage.
                          Lower is better:
                        </p>
                        <ul className="mt-1 text-xs space-y-1">
                          <li>&lt;10%: Excellent accuracy</li>
                          <li>10-20%: Good accuracy</li>
                          <li>20-30%: Reasonable accuracy</li>
                          <li>&gt;30%: Use with caution</li>
                        </ul>
                      </TooltipContent>
                    </UITooltip>
                  </div>
                  <p className="font-medium">{model_accuracy.mape}%</p>
                </div>
              )}
              {model_accuracy.r_squared && (
                <div>
                  <div className="flex items-center gap-1">
                    <span className="text-gray-500">Model Fit (R²)</span>
                    <UITooltip>
                      <TooltipTrigger>
                        <HelpCircle className="h-3 w-3 text-gray-400" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs">
                        <p>
                          <strong>
                            R-squared (Coefficient of Determination)
                          </strong>
                        </p>
                        <p className="mt-1">
                          Measures how well the model explains spending
                          patterns. Higher is better:
                        </p>
                        <ul className="mt-1 text-xs space-y-1">
                          <li>&gt;90%: Excellent fit</li>
                          <li>70-90%: Good fit</li>
                          <li>50-70%: Moderate fit</li>
                          <li>&lt;50%: Weak fit</li>
                        </ul>
                      </TooltipContent>
                    </UITooltip>
                  </div>
                  <p className="font-medium">
                    {(model_accuracy.r_squared * 100).toFixed(1)}%
                  </p>
                </div>
              )}
              <div>
                <div className="flex items-center gap-1">
                  <span className="text-gray-500">Forecast Horizon</span>
                  <UITooltip>
                    <TooltipTrigger>
                      <HelpCircle className="h-3 w-3 text-gray-400" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>
                        How far into the future the model is predicting. Shorter
                        horizons are typically more accurate than longer ones.
                      </p>
                    </TooltipContent>
                  </UITooltip>
                </div>
                <p className="font-medium">{forecastMonths} months</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </TooltipProvider>
    </div>
  );
}
