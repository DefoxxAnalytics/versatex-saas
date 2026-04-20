/**
 * LLM Usage Dashboard Component
 *
 * Displays LLM usage metrics and cost tracking for AI Insights:
 * - Total requests, tokens, and costs
 * - Cache efficiency metrics
 * - Usage breakdown by request type and provider
 * - Daily usage trends
 */

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/StatCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import {
  DollarSign,
  Zap,
  Database,
  Clock,
  TrendingUp,
  BarChart3,
  Cpu,
  RefreshCw,
  Percent,
} from "lucide-react";
import {
  useLLMUsageSummary,
  useLLMUsageDaily,
  formatCost,
  formatTokenCount,
  getRequestTypeLabel,
  getRequestTypeColor,
  getProviderLabel,
} from "@/hooks/useAIInsights";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const CHART_COLORS = [
  "#3b82f6", // blue
  "#8b5cf6", // purple
  "#6366f1", // indigo
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
];

export function LLMUsageDashboard() {
  const [periodDays, setPeriodDays] = useState(30);

  const {
    data: usage,
    isLoading: usageLoading,
    refetch: refetchUsage,
  } = useLLMUsageSummary(periodDays);

  const { data: dailyUsage, isLoading: dailyLoading } =
    useLLMUsageDaily(periodDays);

  const isLoading = usageLoading || dailyLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80">
            <SkeletonCard />
          </div>
          <div className="h-80">
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  if (!usage) {
    return (
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6">
          <div className="text-center py-12 text-muted-foreground">
            <Database className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No usage data available</p>
            <p className="text-sm mt-1">
              LLM usage will be tracked when AI features are used
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const estimatedSavings =
    usage.prompt_cache_tokens_saved * 0.000003 * 0.9 +
    (usage.total_requests * usage.cache_hit_rate / 100) * 0.003;

  return (
    <div className="space-y-6">
      {/* Header with Period Selector */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Cpu className="h-5 w-5 text-blue-600" />
            LLM Usage & Cost Dashboard
          </h2>
          <p className="text-sm text-muted-foreground">
            Monitor AI API usage and cache efficiency
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={periodDays.toString()}
            onValueChange={(v) => setPeriodDays(Number(v))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="60">Last 60 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetchUsage()}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Requests"
          value={usage.total_requests.toLocaleString()}
          description={`Last ${periodDays} days`}
          icon={Zap}
        />
        <StatCard
          title="Total Cost"
          value={formatCost(usage.total_cost_usd)}
          description="API charges"
          icon={DollarSign}
          className="border-amber-200 bg-amber-50"
        />
        <StatCard
          title="Cache Hit Rate"
          value={`${usage.cache_hit_rate.toFixed(1)}%`}
          description="Semantic + Redis cache"
          icon={Database}
          className={
            usage.cache_hit_rate > 50
              ? "border-green-200 bg-green-50"
              : "border-yellow-200 bg-yellow-50"
          }
        />
        <StatCard
          title="Est. Savings"
          value={formatCost(estimatedSavings)}
          description="From caching"
          icon={TrendingUp}
          className="border-green-200 bg-green-50"
        />
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-0 shadow-sm">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Tokens</p>
                <p className="text-2xl font-bold">
                  {formatTokenCount(usage.total_tokens)}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                <BarChart3 className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Latency</p>
                <p className="text-2xl font-bold">
                  {usage.avg_latency_ms.toFixed(0)}ms
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                <Clock className="h-5 w-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Cache Tokens Saved</p>
                <p className="text-2xl font-bold">
                  {formatTokenCount(usage.prompt_cache_tokens_saved)}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                <Percent className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage by Request Type */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="text-base">Usage by Request Type</CardTitle>
            <CardDescription>
              Distribution of requests across different operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            {usage.by_request_type.length > 0 ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={usage.by_request_type.map((item) => ({
                        name: getRequestTypeLabel(item.request_type),
                        value: item.count,
                        cost: item.cost,
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {usage.by_request_type.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number, name: string, props) => [
                        `${value} requests (${formatCost(props?.payload?.cost ?? 0)})`,
                        name,
                      ]}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2">
                  {usage.by_request_type.map((item) => (
                    <div
                      key={item.request_type}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="secondary"
                          className={getRequestTypeColor(item.request_type)}
                        >
                          {getRequestTypeLabel(item.request_type)}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <span className="font-medium">{item.count}</span>
                        <span className="text-muted-foreground ml-2">
                          ({formatCost(item.cost)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No request data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Usage by Provider */}
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="text-base">Usage by Provider</CardTitle>
            <CardDescription>
              LLM provider distribution and costs
            </CardDescription>
          </CardHeader>
          <CardContent>
            {usage.by_provider.length > 0 ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={usage.by_provider.map((item) => ({
                      name: getProviderLabel(item.provider),
                      requests: item.count,
                      cost: item.cost,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis yAxisId="left" orientation="left" stroke="#3b82f6" />
                    <YAxis yAxisId="right" orientation="right" stroke="#10b981" />
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        name === "cost" ? formatCost(value) : value,
                        name === "cost" ? "Cost" : "Requests",
                      ]}
                    />
                    <Bar
                      yAxisId="left"
                      dataKey="requests"
                      fill="#3b82f6"
                      name="Requests"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      yAxisId="right"
                      dataKey="cost"
                      fill="#10b981"
                      name="Cost"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
                <div className="space-y-2">
                  {usage.by_provider.map((item, index) => (
                    <div
                      key={item.provider}
                      className="flex items-center justify-between text-sm p-2 rounded-lg bg-gray-50"
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{
                            backgroundColor:
                              CHART_COLORS[index % CHART_COLORS.length],
                          }}
                        />
                        <span className="font-medium">
                          {getProviderLabel(item.provider)}
                        </span>
                      </div>
                      <div className="text-right">
                        <span>{item.count.toLocaleString()} requests</span>
                        <span className="text-muted-foreground ml-2">
                          ({formatCost(item.cost)})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No provider data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Daily Usage Trend */}
      {dailyUsage && dailyUsage.daily_usage.length > 0 && (
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <CardTitle className="text-base">Daily Usage Trend</CardTitle>
            <CardDescription>
              Requests and costs over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={dailyUsage.daily_usage.map((entry) => ({
                  date: new Date(entry.date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  }),
                  requests: entry.requests,
                  cost: entry.cost,
                  tokens: entry.input_tokens + entry.output_tokens,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" orientation="left" stroke="#3b82f6" />
                <YAxis yAxisId="right" orientation="right" stroke="#10b981" />
                <Tooltip
                  formatter={(value: number, name: string) => {
                    if (name === "cost") return [formatCost(value), "Cost"];
                    if (name === "tokens")
                      return [formatTokenCount(value), "Tokens"];
                    return [value, "Requests"];
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="requests"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  name="Requests"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cost"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  name="Cost"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Cache Efficiency Card */}
      <Card className="border-0 shadow-lg bg-gradient-to-r from-green-50 to-emerald-50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-green-600" />
            <CardTitle className="text-base text-green-900">
              Cache Efficiency Summary
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground mb-1">
                Semantic Cache Hit Rate
              </p>
              <p className="text-2xl font-bold text-green-700">
                {usage.cache_hit_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Similar queries served from cache
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground mb-1">
                Prompt Cache Tokens
              </p>
              <p className="text-2xl font-bold text-blue-700">
                {formatTokenCount(usage.prompt_cache_tokens_saved)}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                System prompt tokens cached (90% savings)
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground mb-1">
                Estimated Total Savings
              </p>
              <p className="text-2xl font-bold text-emerald-700">
                {formatCost(estimatedSavings)}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Combined caching benefits
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
