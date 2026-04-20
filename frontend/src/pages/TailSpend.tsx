import {
  useDetailedTailSpend,
  useTailSpendCategoryDrilldown,
  useTailSpendVendorDrilldown,
} from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import {
  Package,
  BarChart as BarChartIcon,
  Info,
  Lightbulb,
  Target,
  DollarSign,
  Calendar,
  Layers,
  X,
  TrendingUp,
  MapPin,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
} from "recharts";

export default function TailSpend() {
  const [threshold, setThreshold] = useState(50000);
  const [activeTab, setActiveTab] = useState<
    "multi-category" | "category" | "geographic"
  >("category");
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(
    null,
  );
  const [selectedVendorId, setSelectedVendorId] = useState<number | null>(null);

  // Fetch data from backend
  const { data, isLoading, error } = useDetailedTailSpend(threshold);
  const { data: categoryDrilldown, isLoading: categoryLoading } =
    useTailSpendCategoryDrilldown(selectedCategoryId, threshold);
  const { data: vendorDrilldown, isLoading: vendorLoading } =
    useTailSpendVendorDrilldown(selectedVendorId, threshold);

  // Format currency
  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
    return `$${value.toFixed(0)}`;
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
        <span className="ml-2 text-muted-foreground">
          Loading tail spend analysis...
        </span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load tail spend data. Please try again later.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const {
    summary,
    segments,
    pareto_data,
    category_analysis,
    consolidation_opportunities,
  } = data;

  // Prepare Pareto chart data with cumulative percentage
  const paretoChartData = pareto_data.map((item) => ({
    supplier:
      item.supplier.length > 15
        ? item.supplier.substring(0, 15) + "..."
        : item.supplier,
    fullName: item.supplier,
    spend: item.spend,
    cumulative: item.cumulative_pct,
    fill: item.is_tail ? "#ef4444" : "#3b82f6",
    supplier_id: item.supplier_id,
    is_tail: item.is_tail,
  }));

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-purple-600">
        <Package className="h-6 w-6" />
        <h1 className="text-2xl font-bold">
          Tail Spend Analysis & Vendor Consolidation Opportunities
        </h1>
      </div>

      {/* Tail Spend Definition */}
      <Card className="bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                What is Tail Spend?
              </h3>
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>Tail spend</strong> refers to suppliers with annual
                spend below the threshold. These vendors typically represent a
                large portion of the vendor base but a smaller percentage of
                total spend. Consolidating tail spend can reduce administrative
                overhead, improve compliance, and unlock significant savings
                opportunities.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Threshold Control */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium text-muted-foreground mb-2 block">
                Tail Spend Threshold
              </label>
              <div className="flex items-center gap-4">
                <Slider
                  value={[threshold]}
                  onValueChange={(values) => setThreshold(values[0])}
                  min={10000}
                  max={100000}
                  step={5000}
                  className="flex-1"
                />
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">$</span>
                  <Input
                    type="number"
                    value={threshold}
                    onChange={(e) =>
                      setThreshold(
                        Math.max(
                          10000,
                          Math.min(100000, parseInt(e.target.value) || 50000),
                        ),
                      )
                    }
                    className="w-24"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Vendors with annual spend below this threshold are classified as
                tail vendors
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-blue-600">
              {summary.total_vendors}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Total Vendors
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-purple-600">
              {summary.tail_vendor_count}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Tail Vendors ({summary.vendor_ratio.toFixed(0)}%)
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-green-600">
              {formatCurrency(summary.tail_spend)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">Tail Spend</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-orange-600">
              {summary.tail_percentage.toFixed(1)}%
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              % of Total Spend
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-red-600">
              {formatCurrency(summary.savings_opportunity)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Savings Opportunity
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Vendor Pareto Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChartIcon className="h-5 w-5 text-blue-600" />
            Vendor Pareto Analysis (80/20 Rule)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={paretoChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="supplier"
                angle={-45}
                textAnchor="end"
                height={150}
                interval={0}
                tick={{ fontSize: 10 }}
              />
              <YAxis
                yAxisId="left"
                label={{
                  value: "Annual Spend ($)",
                  angle: -90,
                  position: "insideLeft",
                }}
                tickFormatter={(value) => formatCurrency(value)}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                label={{
                  value: "Cumulative %",
                  angle: 90,
                  position: "insideRight",
                }}
                domain={[0, 100]}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const item = payload[0].payload;
                    return (
                      <div className="bg-white dark:bg-gray-800 p-3 border rounded shadow-lg">
                        <p className="font-semibold">{item.fullName}</p>
                        <p className="text-sm">
                          Spend: {formatCurrency(item.spend)}
                        </p>
                        <p className="text-sm">
                          Cumulative: {item.cumulative.toFixed(1)}%
                        </p>
                        <p
                          className={`text-sm font-medium ${item.is_tail ? "text-red-600" : "text-blue-600"}`}
                        >
                          {item.is_tail ? "Tail Vendor" : "Strategic Vendor"}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend />
              <Bar
                yAxisId="left"
                dataKey="spend"
                name="Vendor Spend"
                onClick={(data) => setSelectedVendorId(data.supplier_id)}
                cursor="pointer"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative"
                stroke="#f97316"
                strokeWidth={2}
                name="Cumulative %"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="mt-4 flex items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span>Non-Tail Vendors (&gt;{formatCurrency(threshold)})</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span>Tail Vendors (&lt;{formatCurrency(threshold)})</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tail Vendor Segmentation */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-teal-600">
          <Target className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Tail Vendor Segmentation</h2>
        </div>

        {/* Segmentation Definitions */}
        <Card className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950 border-purple-200 dark:border-purple-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-4">
              <Info className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              <h3 className="font-semibold text-purple-900 dark:text-purple-100">
                Tail Vendor Segmentation Definitions
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div>
                  <span className="font-semibold">Micro:</span>
                  <span className="text-sm text-muted-foreground ml-1">
                    &lt; $10,000 annual spend
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div>
                  <span className="font-semibold">Small:</span>
                  <span className="text-sm text-muted-foreground ml-1">
                    $10,000 - {formatCurrency(threshold)} annual spend
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <div>
                  <span className="font-semibold">Non-Tail:</span>
                  <span className="text-sm text-muted-foreground ml-1">
                    &gt; {formatCurrency(threshold)} annual spend
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Segment Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Micro Vendors */}
          <Card className="border-l-4 border-l-red-500">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-red-600">Micro Vendors</span>
                <span className="text-sm text-muted-foreground">&lt; $10K</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-2xl font-bold">
                  {segments.micro.count} Vendors
                </div>
                <div className="text-sm text-muted-foreground">
                  Total Vendors
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {formatCurrency(segments.micro.spend)}
                </div>
                <div className="text-sm text-muted-foreground">Total Spend</div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {segments.micro.transactions.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  Transactions
                </div>
              </div>
              <div className="flex items-start gap-2 mt-4 p-3 bg-yellow-50 dark:bg-yellow-950 rounded-lg border border-yellow-200 dark:border-yellow-800">
                <Lightbulb className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-yellow-900 dark:text-yellow-100">
                  <span className="font-semibold">Recommendation:</span>{" "}
                  Consolidate or eliminate to reduce administrative overhead
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Small Vendors */}
          <Card className="border-l-4 border-l-yellow-500">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-yellow-600">Small Vendors</span>
                <span className="text-sm text-muted-foreground">
                  $10K - {formatCurrency(threshold)}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-2xl font-bold">
                  {segments.small.count} Vendors
                </div>
                <div className="text-sm text-muted-foreground">
                  Total Vendors
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {formatCurrency(segments.small.spend)}
                </div>
                <div className="text-sm text-muted-foreground">Total Spend</div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {segments.small.transactions.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  Transactions
                </div>
              </div>
              <div className="flex items-start gap-2 mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                <Lightbulb className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-900 dark:text-blue-100">
                  <span className="font-semibold">Recommendation:</span>{" "}
                  Negotiate better terms and implement process improvements
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Non-Tail Vendors */}
          <Card className="border-l-4 border-l-green-500">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-green-600">Non-Tail Vendors</span>
                <span className="text-sm text-muted-foreground">
                  &gt; {formatCurrency(threshold)}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-2xl font-bold">
                  {segments.non_tail.count} Vendors
                </div>
                <div className="text-sm text-muted-foreground">
                  Total Vendors
                </div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {formatCurrency(segments.non_tail.spend)}
                </div>
                <div className="text-sm text-muted-foreground">Total Spend</div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {segments.non_tail.transactions.toLocaleString()}
                </div>
                <div className="text-sm text-muted-foreground">
                  Transactions
                </div>
              </div>
              <div className="flex items-start gap-2 mt-4 p-3 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
                <Lightbulb className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-green-900 dark:text-green-100">
                  <span className="font-semibold">Recommendation:</span>{" "}
                  Strategic partnerships and volume consolidation
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Savings Opportunities & Strategic Recommendations */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-orange-600">
              <DollarSign className="h-5 w-5" />
              <CardTitle>
                Savings Opportunities & Strategic Recommendations
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Vendor Consolidation */}
            <div className="border-l-4 border-l-blue-500 pl-4 py-2">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg">Vendor Consolidation</h3>
                <span className="text-sm text-muted-foreground">
                  3-6 months
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Consolidate micro vendors to reduce administrative overhead
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Conservative Savings
                  </div>
                  <div className="text-xl font-bold text-blue-600">
                    {formatCurrency(segments.micro.spend * 0.105)}
                  </div>
                </div>
                <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Optimistic Savings
                  </div>
                  <div className="text-xl font-bold text-blue-600">
                    {formatCurrency(segments.micro.spend * 0.15)}
                  </div>
                </div>
                <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Vendors Affected
                  </div>
                  <div className="text-xl font-bold text-blue-600">
                    {segments.micro.count}
                  </div>
                </div>
              </div>
            </div>

            {/* Process Improvement */}
            <div className="border-l-4 border-l-green-500 pl-4 py-2">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg">Process Improvement</h3>
                <span className="text-sm text-muted-foreground">
                  2-4 months
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Streamline procurement processes for tail spend
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-50 dark:bg-green-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Conservative Savings
                  </div>
                  <div className="text-xl font-bold text-green-600">
                    {formatCurrency(summary.tail_spend * 0.06)}
                  </div>
                </div>
                <div className="bg-green-50 dark:bg-green-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Optimistic Savings
                  </div>
                  <div className="text-xl font-bold text-green-600">
                    {formatCurrency(summary.tail_spend * 0.1)}
                  </div>
                </div>
                <div className="bg-green-50 dark:bg-green-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Vendors Affected
                  </div>
                  <div className="text-xl font-bold text-green-600">
                    {summary.tail_vendor_count}
                  </div>
                </div>
              </div>
            </div>

            {/* Contract Optimization */}
            <div className="border-l-4 border-l-purple-500 pl-4 py-2">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg">Contract Optimization</h3>
                <span className="text-sm text-muted-foreground">
                  4-8 months
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Negotiate better terms with small vendors
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-purple-50 dark:bg-purple-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Conservative Savings
                  </div>
                  <div className="text-xl font-bold text-purple-600">
                    {formatCurrency(segments.small.spend * 0.105)}
                  </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Optimistic Savings
                  </div>
                  <div className="text-xl font-bold text-purple-600">
                    {formatCurrency(segments.small.spend * 0.14)}
                  </div>
                </div>
                <div className="bg-purple-50 dark:bg-purple-950 p-3 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Vendors Affected
                  </div>
                  <div className="text-xl font-bold text-purple-600">
                    {segments.small.count}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Plan - Implementation Timeline */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-blue-600">
              <Calendar className="h-5 w-5" />
              <CardTitle>Action Plan - Implementation Timeline</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Phase 1: Quick Wins */}
            <div className="border-l-4 border-l-green-500 bg-green-50 dark:bg-green-950 p-4 rounded-r-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg text-green-700 dark:text-green-300">
                  Phase 1: Quick Wins
                </h3>
                <span className="text-sm font-medium text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900 px-3 py-1 rounded-full">
                  0-3 months
                </span>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-1">
                    •
                  </span>
                  <span>
                    Identify micro vendors for immediate consolidation
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-1">
                    •
                  </span>
                  <span>Implement basic process improvements</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-1">
                    •
                  </span>
                  <span>Set up vendor performance tracking</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-1">
                    •
                  </span>
                  <span>Establish procurement governance framework</span>
                </li>
              </ul>
            </div>

            {/* Phase 2: Strategic Implementation */}
            <div className="border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-950 p-4 rounded-r-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg text-blue-700 dark:text-blue-300">
                  Phase 2: Strategic Implementation
                </h3>
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900 px-3 py-1 rounded-full">
                  3-6 months
                </span>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-1">
                    •
                  </span>
                  <span>Execute vendor consolidation strategy</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-1">
                    •
                  </span>
                  <span>Negotiate improved contracts with small vendors</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-1">
                    •
                  </span>
                  <span>Implement automated procurement workflows</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-1">
                    •
                  </span>
                  <span>Roll out vendor management system</span>
                </li>
              </ul>
            </div>

            {/* Phase 3: Optimization */}
            <div className="border-l-4 border-l-purple-500 bg-purple-50 dark:bg-purple-950 p-4 rounded-r-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-lg text-purple-700 dark:text-purple-300">
                  Phase 3: Optimization
                </h3>
                <span className="text-sm font-medium text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900 px-3 py-1 rounded-full">
                  6-12 months
                </span>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-purple-600 dark:text-purple-400 mt-1">
                    •
                  </span>
                  <span>Monitor and optimize new processes</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-600 dark:text-purple-400 mt-1">
                    •
                  </span>
                  <span>Measure savings realization</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-600 dark:text-purple-400 mt-1">
                    •
                  </span>
                  <span>Continuous improvement initiatives</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-600 dark:text-purple-400 mt-1">
                    •
                  </span>
                  <span>Review and refine vendor relationships</span>
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Category-Level Tail Analysis */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-purple-600">
              <Layers className="h-5 w-5" />
              <CardTitle>Category-Level Tail Analysis</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Click on a category to see detailed vendor breakdown
            </p>
            <div className="space-y-4">
              {category_analysis.slice(0, 10).map((cat, index) => (
                <div
                  key={index}
                  className="border-l-4 border-l-gray-300 bg-gray-50 dark:bg-gray-900 p-4 rounded-r-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  onClick={() =>
                    cat.category_id && setSelectedCategoryId(cat.category_id)
                  }
                >
                  <h3 className="font-semibold text-lg mb-2">{cat.category}</h3>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="font-medium">
                        {cat.tail_percentage.toFixed(1)}%
                      </span>
                      <span className="text-muted-foreground ml-1">Tail %</span>
                    </div>
                    <div>
                      <span className="font-medium">
                        {cat.vendor_percentage.toFixed(0)}%
                      </span>
                      <span className="text-muted-foreground ml-1">
                        Vendor %
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">
                        {formatCurrency(cat.tail_spend)}
                      </span>
                      <span className="text-muted-foreground ml-1">
                        Tail Spend
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">{cat.tail_vendors}</span>
                      <span className="text-muted-foreground ml-1">
                        Tail Vendors
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Intelligent Vendor Consolidation Opportunities */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-indigo-600">
              <Lightbulb className="h-5 w-5" />
              <CardTitle>
                Intelligent Vendor Consolidation Opportunities
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Strategic opportunities to consolidate vendors and reduce
              complexity.
            </p>

            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">
                  Total Opportunities
                </div>
                <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                  {consolidation_opportunities.total_opportunities}
                </div>
              </div>
              <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="text-sm text-green-600 dark:text-green-400 font-medium mb-1">
                  Total Savings Potential
                </div>
                <div className="text-2xl font-bold text-green-900 dark:text-green-100">
                  {formatCurrency(consolidation_opportunities.total_savings)}
                </div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                <div className="text-sm text-purple-600 dark:text-purple-400 font-medium mb-1">
                  Top Opportunity Type
                </div>
                <div className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                  {consolidation_opportunities.top_type}
                </div>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-2 mb-4 border-b dark:border-gray-700">
              <Button
                variant={activeTab === "multi-category" ? "default" : "ghost"}
                onClick={() => setActiveTab("multi-category")}
                className="rounded-b-none"
              >
                Multi-Category Vendors
              </Button>
              <Button
                variant={activeTab === "category" ? "default" : "ghost"}
                onClick={() => setActiveTab("category")}
                className="rounded-b-none"
              >
                Category Consolidation
              </Button>
              <Button
                variant={activeTab === "geographic" ? "default" : "ghost"}
                onClick={() => setActiveTab("geographic")}
                className="rounded-b-none"
              >
                Geographic Consolidation
              </Button>
            </div>

            {/* Tab Content */}
            <div className="mt-4">
              {activeTab === "multi-category" && (
                <div>
                  {consolidation_opportunities.multi_category.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      <p>No multi-category vendor opportunities identified.</p>
                      <p className="text-sm mt-2">
                        All tail vendors operate in a single category.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {consolidation_opportunities.multi_category.map(
                        (opp, index) => (
                          <div
                            key={index}
                            className="border-l-4 border-l-indigo-500 bg-indigo-50 dark:bg-indigo-950 p-4 rounded-r-lg cursor-pointer hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
                            onClick={() => setSelectedVendorId(opp.supplier_id)}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <h3 className="font-semibold text-lg text-indigo-900 dark:text-indigo-100">
                                {opp.supplier}
                              </h3>
                              <span className="text-sm font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900 px-2 py-1 rounded">
                                {opp.category_count} Categories
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                              <div>
                                <span className="font-medium">
                                  Total Spend:
                                </span>{" "}
                                {formatCurrency(opp.total_spend)}
                              </div>
                              <div>
                                <span className="font-medium">
                                  Savings Potential:
                                </span>{" "}
                                {formatCurrency(opp.savings_potential)}
                              </div>
                            </div>
                            <div className="text-sm text-muted-foreground">
                              <span className="font-medium">Categories:</span>{" "}
                              {opp.categories.join(", ")}
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "category" && (
                <div className="space-y-3">
                  {consolidation_opportunities.category.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      <p>No category consolidation opportunities identified.</p>
                    </div>
                  ) : (
                    consolidation_opportunities.category.map((opp, index) => (
                      <div
                        key={index}
                        className="border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-950 p-4 rounded-r-lg cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
                        onClick={() =>
                          opp.category_id &&
                          setSelectedCategoryId(opp.category_id)
                        }
                      >
                        <h3 className="font-semibold text-lg text-blue-900 dark:text-blue-100 mb-2">
                          {opp.category}
                        </h3>
                        <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                          <div>
                            <span className="font-medium">Total Vendors:</span>{" "}
                            {opp.total_vendors}
                          </div>
                          <div>
                            <span className="font-medium">Tail Vendors:</span>{" "}
                            {opp.tail_vendors}
                          </div>
                          <div>
                            <span className="font-medium">Tail Spend:</span>{" "}
                            {formatCurrency(opp.tail_spend)}
                          </div>
                          <div>
                            <span className="font-medium">
                              Savings Potential:
                            </span>{" "}
                            {formatCurrency(opp.savings_potential)}
                          </div>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <span className="font-medium">Top Vendor:</span>{" "}
                          {opp.top_vendor}
                        </div>
                        <div className="mt-2 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded p-2 flex items-start gap-2">
                          <Lightbulb className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5" />
                          <p className="text-xs text-yellow-800 dark:text-yellow-200">
                            <strong>Recommendation:</strong> Consolidate{" "}
                            {opp.tail_vendors} tail vendors to reduce
                            administrative overhead and negotiate better rates.
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === "geographic" && (
                <div className="space-y-3">
                  {consolidation_opportunities.geographic.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      <p>
                        No geographic consolidation opportunities identified.
                      </p>
                    </div>
                  ) : (
                    consolidation_opportunities.geographic.map((opp, index) => (
                      <div
                        key={index}
                        className="border-l-4 border-l-green-500 bg-green-50 dark:bg-green-950 p-4 rounded-r-lg"
                      >
                        <h3 className="font-semibold text-lg text-green-900 dark:text-green-100 mb-2">
                          {opp.location}
                        </h3>
                        <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                          <div>
                            <span className="font-medium">Total Vendors:</span>{" "}
                            {opp.total_vendors}
                          </div>
                          <div>
                            <span className="font-medium">Tail Vendors:</span>{" "}
                            {opp.tail_vendors}
                          </div>
                          <div>
                            <span className="font-medium">Tail Spend:</span>{" "}
                            {formatCurrency(opp.tail_spend)}
                          </div>
                          <div>
                            <span className="font-medium">
                              Savings Potential:
                            </span>{" "}
                            {formatCurrency(opp.savings_potential)}
                          </div>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <span className="font-medium">Top Vendor:</span>{" "}
                          {opp.top_vendor}
                        </div>
                        <div className="mt-2 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded p-2 flex items-start gap-2">
                          <Lightbulb className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5" />
                          <p className="text-xs text-yellow-800 dark:text-yellow-200">
                            <strong>Recommendation:</strong> Consolidate{" "}
                            {opp.tail_vendors} tail vendors in {opp.location} to
                            leverage regional purchasing power.
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Drill-Down Modal */}
      <Dialog
        open={!!selectedCategoryId}
        onOpenChange={() => setSelectedCategoryId(null)}
      >
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-purple-600" />
              {categoryDrilldown?.category || "Category"} - Vendor Breakdown
            </DialogTitle>
          </DialogHeader>

          {categoryLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
              <span className="ml-2 text-muted-foreground">Loading...</span>
            </div>
          ) : categoryDrilldown ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Total Spend
                  </div>
                  <div className="text-xl font-bold">
                    {formatCurrency(categoryDrilldown.total_spend)}
                  </div>
                </div>
                <div className="bg-red-50 dark:bg-red-950 p-4 rounded-lg">
                  <div className="text-sm text-red-600 dark:text-red-400">
                    Tail Spend
                  </div>
                  <div className="text-xl font-bold text-red-700 dark:text-red-300">
                    {formatCurrency(categoryDrilldown.tail_spend)}
                  </div>
                </div>
                <div className="bg-orange-50 dark:bg-orange-950 p-4 rounded-lg">
                  <div className="text-sm text-orange-600 dark:text-orange-400">
                    Tail %
                  </div>
                  <div className="text-xl font-bold text-orange-700 dark:text-orange-300">
                    {categoryDrilldown.tail_percentage.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              {categoryDrilldown.recommendations.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 p-4 rounded-lg">
                  <h4 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-2 flex items-center gap-2">
                    <Lightbulb className="h-4 w-4" />
                    Recommendations
                  </h4>
                  <ul className="space-y-1">
                    {categoryDrilldown.recommendations.map((rec, idx) => (
                      <li
                        key={idx}
                        className="text-sm text-yellow-700 dark:text-yellow-300 flex items-start gap-2"
                      >
                        <span className="mt-1">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Vendors Table */}
              <div>
                <h4 className="font-semibold mb-3">Vendors in Category</h4>
                <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="text-left p-3">Vendor</th>
                        <th className="text-right p-3">Spend</th>
                        <th className="text-right p-3">Transactions</th>
                        <th className="text-right p-3">% of Category</th>
                        <th className="text-center p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryDrilldown.vendors.map((vendor, idx) => (
                        <tr
                          key={idx}
                          className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                          onClick={() => {
                            setSelectedCategoryId(null);
                            setSelectedVendorId(vendor.supplier_id);
                          }}
                        >
                          <td className="p-3 font-medium">{vendor.name}</td>
                          <td className="p-3 text-right">
                            {formatCurrency(vendor.spend)}
                          </td>
                          <td className="p-3 text-right">
                            {vendor.transaction_count}
                          </td>
                          <td className="p-3 text-right">
                            {vendor.percent_of_category.toFixed(1)}%
                          </td>
                          <td className="p-3 text-center">
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                vendor.is_tail
                                  ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                                  : "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                              }`}
                            >
                              {vendor.is_tail ? "Tail" : "Strategic"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">No data available</p>
          )}
        </DialogContent>
      </Dialog>

      {/* Vendor Drill-Down Modal */}
      <Dialog
        open={!!selectedVendorId}
        onOpenChange={() => setSelectedVendorId(null)}
      >
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-blue-600" />
              {vendorDrilldown?.supplier || "Vendor"} - Details
            </DialogTitle>
          </DialogHeader>

          {vendorLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
              <span className="ml-2 text-muted-foreground">Loading...</span>
            </div>
          ) : vendorDrilldown ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Total Spend
                  </div>
                  <div className="text-xl font-bold">
                    {formatCurrency(vendorDrilldown.total_spend)}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Transactions
                  </div>
                  <div className="text-xl font-bold">
                    {vendorDrilldown.transaction_count}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <div className="text-sm text-muted-foreground">
                    Categories
                  </div>
                  <div className="text-xl font-bold">
                    {vendorDrilldown.categories.length}
                  </div>
                </div>
                <div
                  className={`p-4 rounded-lg ${vendorDrilldown.is_tail ? "bg-red-50 dark:bg-red-950" : "bg-green-50 dark:bg-green-950"}`}
                >
                  <div
                    className={`text-sm ${vendorDrilldown.is_tail ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}
                  >
                    Status
                  </div>
                  <div
                    className={`text-xl font-bold ${vendorDrilldown.is_tail ? "text-red-700 dark:text-red-300" : "text-green-700 dark:text-green-300"}`}
                  >
                    {vendorDrilldown.is_tail ? "Tail Vendor" : "Strategic"}
                  </div>
                </div>
              </div>

              {/* Monthly Spend Chart */}
              {vendorDrilldown.monthly_spend.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Monthly Spend Trend (Last 12 Months)
                  </h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={vendorDrilldown.monthly_spend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                      <YAxis tickFormatter={(value) => formatCurrency(value)} />
                      <Tooltip
                        formatter={(value: number) => [
                          formatCurrency(value),
                          "Spend",
                        ]}
                      />
                      <Bar dataKey="spend" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Category Breakdown */}
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  Category Breakdown
                </h4>
                <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="text-left p-3">Category</th>
                        <th className="text-right p-3">Spend</th>
                        <th className="text-right p-3">Transactions</th>
                        <th className="text-right p-3">% of Vendor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendorDrilldown.categories.map((cat, idx) => (
                        <tr key={idx} className="border-t dark:border-gray-700">
                          <td className="p-3 font-medium">{cat.name}</td>
                          <td className="p-3 text-right">
                            {formatCurrency(cat.spend)}
                          </td>
                          <td className="p-3 text-right">
                            {cat.transaction_count}
                          </td>
                          <td className="p-3 text-right">
                            {cat.percent_of_vendor.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Location Breakdown */}
              {vendorDrilldown.locations.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    Location Breakdown
                  </h4>
                  <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          <th className="text-left p-3">Location</th>
                          <th className="text-right p-3">Spend</th>
                          <th className="text-right p-3">Transactions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {vendorDrilldown.locations.map((loc, idx) => (
                          <tr
                            key={idx}
                            className="border-t dark:border-gray-700"
                          >
                            <td className="p-3 font-medium">{loc.name}</td>
                            <td className="p-3 text-right">
                              {formatCurrency(loc.spend)}
                            </td>
                            <td className="p-3 text-right">
                              {loc.transaction_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground">No data available</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
