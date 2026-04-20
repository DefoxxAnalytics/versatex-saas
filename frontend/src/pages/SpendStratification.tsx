import { useState, useMemo } from "react";
import {
  useDetailedStratification,
  useSegmentDrilldown,
  useBandDrilldown,
} from "@/hooks/useAnalytics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Layers,
  TrendingUp,
  AlertTriangle,
  Target,
  Users,
  DollarSign,
  Eye,
  Package,
  Loader2,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Shield,
  Zap,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";

// Segment colors for charts
const SEGMENT_COLORS: Record<string, string> = {
  Strategic: "#ef4444",
  Leverage: "#f59e0b",
  Routine: "#eab308",
  Tactical: "#10b981",
};

// Sort field type
type SortField =
  | "band"
  | "total_spend"
  | "percent_of_total"
  | "suppliers"
  | "transactions";
type SortDirection = "asc" | "desc";

export default function SpendStratification() {
  const { data, isLoading, error } = useDetailedStratification();
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [selectedBand, setSelectedBand] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<SortField>("total_spend");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [recommendationsExpanded, setRecommendationsExpanded] = useState(true);

  // Fetch drill-down data on-demand
  const { data: segmentDrilldownData, isLoading: segmentDrilldownLoading } =
    useSegmentDrilldown(selectedSegment);
  const { data: bandDrilldownData, isLoading: bandDrilldownLoading } =
    useBandDrilldown(selectedBand);

  // Sorted and filtered spend bands
  const sortedBands = useMemo(() => {
    if (!data?.spend_bands) return [];

    let filtered = data.spend_bands.filter((band) =>
      band.band.toLowerCase().includes(searchTerm.toLowerCase()),
    );

    return filtered.sort((a, b) => {
      let aVal: number | string;
      let bVal: number | string;

      switch (sortField) {
        case "band":
          // Sort by min value for proper band ordering
          aVal = a.min;
          bVal = b.min;
          break;
        case "total_spend":
          aVal = a.total_spend;
          bVal = b.total_spend;
          break;
        case "percent_of_total":
          aVal = a.percent_of_total;
          bVal = b.percent_of_total;
          break;
        case "suppliers":
          aVal = a.suppliers;
          bVal = b.suppliers;
          break;
        case "transactions":
          aVal = a.transactions;
          bVal = b.transactions;
          break;
        default:
          aVal = a.total_spend;
          bVal = b.total_spend;
      }

      if (sortDirection === "asc") {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });
  }, [data?.spend_bands, searchTerm, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-4 w-4 ml-1 opacity-50" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="h-4 w-4 ml-1" />
    ) : (
      <ArrowDown className="h-4 w-4 ml-1" />
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-12 w-12 text-blue-600 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600 dark:text-gray-400">
            Loading spend stratification data...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <AlertTriangle className="h-16 w-16 text-red-500 mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Error Loading Data
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Failed to load spend stratification analysis. Please try again.
        </p>
      </div>
    );
  }

  if (!data || data.spend_bands.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <Layers className="h-16 w-16 text-gray-400 mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          No Data Available
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Upload your procurement data to see spend stratification analysis.
        </p>
      </div>
    );
  }

  const { summary, spend_bands, segments } = data;

  // Calculate strategic and tactical spend from segments
  const strategicSegment = segments.find((s) => s.segment === "Strategic");
  const tacticalSegment = segments.find((s) => s.segment === "Tactical");

  // Risk color mapping
  const getRiskColor = (risk: string) => {
    if (risk.includes("HIGH"))
      return "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300";
    if (risk.includes("MEDIUM"))
      return "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300";
    return "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300";
  };

  // Risk badge component
  const getRiskBadge = (risk: string) => {
    const colors: Record<string, string> = {
      High: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
      Medium:
        "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
      Low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    };
    return <Badge className={colors[risk] || colors.Low}>{risk}</Badge>;
  };

  // Strategic importance badge
  const getImportanceBadge = (importance: string) => {
    const colors: Record<string, string> = {
      Critical:
        "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
      Strategic:
        "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
      Tactical:
        "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
    };
    return (
      <Badge className={colors[importance] || colors.Tactical}>
        {importance}
      </Badge>
    );
  };

  // Prepare chart data with segment reference for click handling
  const chartData = segments.map((seg) => ({
    name: `${seg.segment} (${seg.spend_range})`,
    segment: seg.segment,
    value: seg.total_spend,
    color: SEGMENT_COLORS[seg.segment] || "#6b7280",
    percentage: seg.percent_of_total,
  }));

  // Handle pie chart click
  const handlePieClick = (data: { segment?: string }) => {
    if (data?.segment) {
      setSelectedSegment(data.segment);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Layers className="h-8 w-8 text-blue-600" />
          Spend Stratification
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Analyze spending patterns across different spend bands and supplier
          segments
        </p>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="dark:bg-gray-800 dark:border-gray-700">
          <CardContent className="pt-6 text-center">
            <DollarSign className="h-8 w-8 mx-auto mb-2 text-blue-600" />
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              $
              {summary.total_spend.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Total Spend
            </div>
          </CardContent>
        </Card>

        <Card className="dark:bg-gray-800 dark:border-gray-700">
          <CardContent className="pt-6 text-center">
            <Target className="h-8 w-8 mx-auto mb-2 text-red-500" />
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              $
              {(strategicSegment?.total_spend || 0).toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Strategic Spend
            </div>
            <div className="text-xs text-red-500 mt-1">
              {strategicSegment?.percent_of_total.toFixed(1)}% of total
            </div>
          </CardContent>
        </Card>

        <Card className="dark:bg-gray-800 dark:border-gray-700">
          <CardContent className="pt-6 text-center">
            <Zap className="h-8 w-8 mx-auto mb-2 text-green-500" />
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              $
              {(tacticalSegment?.total_spend || 0).toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Consolidation Opportunity
            </div>
            <div className="text-xs text-green-500 mt-1">
              {tacticalSegment?.suppliers || 0} fragmented suppliers
            </div>
          </CardContent>
        </Card>

        <Card className="dark:bg-gray-800 dark:border-gray-700">
          <CardContent className="pt-6 text-center">
            <Shield className="h-8 w-8 mx-auto mb-2 text-orange-500" />
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {summary.high_risk_bands}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              High Risk Bands
            </div>
            <div className="text-xs text-orange-500 mt-1">
              Concentration concerns
            </div>
          </CardContent>
        </Card>
      </div>

      {/* SpendBand Analysis & Strategic Intelligence Card */}
      <Card className="border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
            <Target className="h-5 w-5" />
            Procurement Specialist SpendBand Analysis & Strategic Intelligence
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.active_spend_bands}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Active SpendBands
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Segmentation complexity
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.strategic_bands}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Strategic Bands
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Requiring executive attention
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.highest_impact_band}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Highest Impact Band
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {summary.highest_impact_percent.toFixed(1)}% of total spend
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.high_risk_bands}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  High Risk Bands
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Concentration concerns
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.most_fragmented_band}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Most Fragmented
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {summary.most_fragmented_suppliers} suppliers
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/80 dark:bg-gray-800/80 border-blue-200 dark:border-blue-700">
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600 mb-1">
                  {summary.complex_bands}
                </div>
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Complex Bands
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Management intensive
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Strategic Analysis */}
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  Procurement Specialist Strategic Analysis
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  <strong>High Concentration Risk:</strong> The{" "}
                  {summary.highest_impact_band} band represents{" "}
                  {summary.highest_impact_percent.toFixed(1)}% of total spend,
                  creating significant exposure.{" "}
                  <strong>Supplier Base Complexity:</strong> Average of{" "}
                  {summary.avg_suppliers_per_band} suppliers per band indicates
                  high management complexity.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                Overall Risk Assessment:
              </span>
              <Badge
                className={`${getRiskColor(summary.overall_risk)} border px-3 py-1`}
              >
                {summary.overall_risk}
              </Badge>
            </div>

            {/* Collapsible Recommendations Panel */}
            {summary.recommendations.length > 0 && (
              <div className="border-l-4 border-blue-400 pl-4 py-2 bg-white/50 dark:bg-gray-800/50 rounded-r">
                <button
                  onClick={() =>
                    setRecommendationsExpanded(!recommendationsExpanded)
                  }
                  className="flex items-center gap-2 mb-2 w-full text-left"
                >
                  <Lightbulb className="h-4 w-4 text-blue-600 flex-shrink-0" />
                  <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm flex-1">
                    Strategic Recommendations ({summary.recommendations.length})
                  </h4>
                  {recommendationsExpanded ? (
                    <ChevronUp className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  )}
                </button>
                {recommendationsExpanded && (
                  <ul className="space-y-1.5 text-sm text-gray-700 dark:text-gray-300">
                    {summary.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-600 mt-0.5">—</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Spend Stratification Chart */}
      <Card className="dark:bg-gray-800 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 dark:text-gray-100">
            <Layers className="h-5 w-5 text-blue-600" />
            Spend Stratification by Supplier Segments
            <span className="text-sm font-normal text-gray-500 ml-2">
              (Click a segment to drill down)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-visible">
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={100}
                outerRadius={160}
                paddingAngle={2}
                dataKey="value"
                onClick={(_, index) => handlePieClick(chartData[index])}
                style={{ cursor: "pointer" }}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(
                  value: number,
                  _name: string,
                  props: { payload?: { percentage?: number } },
                ) => {
                  const percentage = props.payload?.percentage || 0;
                  return [
                    `$${value.toLocaleString()} (${percentage.toFixed(2)}% of total spend)`,
                    "",
                  ];
                }}
                contentStyle={{
                  backgroundColor: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                  padding: "12px",
                  zIndex: 1000,
                }}
                wrapperStyle={{ zIndex: 1000 }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                iconType="circle"
                formatter={(value) => (
                  <span className="text-sm dark:text-gray-300">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Stratification Details Table */}
      <Card className="dark:bg-gray-800 dark:border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 dark:text-gray-100">
            <Target className="h-5 w-5 text-blue-600" />
            Stratification Details
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-gray-300 dark:border-gray-600 bg-gray-800 text-white">
                  <th className="text-left p-3 font-semibold">Segment</th>
                  <th className="text-left p-3 font-semibold">Spend Range</th>
                  <th className="text-right p-3 font-semibold">Total Spend</th>
                  <th className="text-right p-3 font-semibold">% of Total</th>
                  <th className="text-right p-3 font-semibold">Suppliers</th>
                  <th className="text-left p-3 font-semibold">Strategy</th>
                  <th className="text-center p-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {segments.map((segment, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <td className="p-3 font-medium text-gray-900 dark:text-gray-100">
                      {segment.segment}
                    </td>
                    <td className="p-3 text-gray-600 dark:text-gray-300">
                      {segment.spend_range}
                    </td>
                    <td className="p-3 text-right font-semibold text-gray-900 dark:text-gray-100">
                      $
                      {segment.total_spend.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </td>
                    <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                      {segment.percent_of_total.toFixed(2)}%
                    </td>
                    <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                      {segment.suppliers}
                    </td>
                    <td className="p-3 text-gray-600 dark:text-gray-300">
                      {segment.strategy}
                    </td>
                    <td className="p-3 text-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedSegment(segment.segment)}
                        className="gap-1"
                      >
                        <Eye className="h-4 w-4" />
                        View Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* SpendBand Analysis Table with Search and Sorting */}
      <Card className="dark:bg-gray-800 dark:border-gray-700">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <CardTitle className="flex items-center gap-2 dark:text-gray-100">
              <DollarSign className="h-5 w-5 text-blue-600" />
              SpendBand Analysis
            </CardTitle>
            <div className="relative w-full md:w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search spend bands..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-gray-800 text-white z-10">
                <tr className="border-b-2 border-gray-300 dark:border-gray-600">
                  <th
                    className="text-left p-3 font-semibold cursor-pointer hover:bg-gray-700"
                    onClick={() => handleSort("band")}
                  >
                    <div className="flex items-center">
                      SpendBand
                      {getSortIcon("band")}
                    </div>
                  </th>
                  <th
                    className="text-right p-3 font-semibold cursor-pointer hover:bg-gray-700"
                    onClick={() => handleSort("total_spend")}
                  >
                    <div className="flex items-center justify-end">
                      Total Spend
                      {getSortIcon("total_spend")}
                    </div>
                  </th>
                  <th
                    className="text-right p-3 font-semibold cursor-pointer hover:bg-gray-700"
                    onClick={() => handleSort("percent_of_total")}
                  >
                    <div className="flex items-center justify-end">
                      % of Total
                      {getSortIcon("percent_of_total")}
                    </div>
                  </th>
                  <th
                    className="text-right p-3 font-semibold cursor-pointer hover:bg-gray-700"
                    onClick={() => handleSort("suppliers")}
                  >
                    <div className="flex items-center justify-end">
                      Suppliers
                      {getSortIcon("suppliers")}
                    </div>
                  </th>
                  <th
                    className="text-right p-3 font-semibold cursor-pointer hover:bg-gray-700"
                    onClick={() => handleSort("transactions")}
                  >
                    <div className="flex items-center justify-end">
                      Transactions
                      {getSortIcon("transactions")}
                    </div>
                  </th>
                  <th className="text-center p-3 font-semibold">Risk Level</th>
                  <th className="text-center p-3 font-semibold">Importance</th>
                  <th className="text-center p-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedBands.map((band, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                    onClick={() => setSelectedBand(band.band)}
                  >
                    <td className="p-3 font-medium text-gray-900 dark:text-gray-100">
                      {band.band}
                    </td>
                    <td className="p-3 text-right font-semibold text-gray-900 dark:text-gray-100">
                      $
                      {band.total_spend.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </td>
                    <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                      {band.percent_of_total.toFixed(2)}%
                    </td>
                    <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                      {band.suppliers}
                    </td>
                    <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                      {band.transactions.toLocaleString()}
                    </td>
                    <td className="p-3 text-center">
                      {getRiskBadge(band.risk_level)}
                    </td>
                    <td className="p-3 text-center">
                      {getImportanceBadge(band.strategic_importance)}
                    </td>
                    <td className="p-3 text-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedBand(band.band);
                        }}
                        className="gap-1"
                      >
                        <Eye className="h-4 w-4" />
                        Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Segment Drill-Through Modal */}
      <Dialog
        open={!!selectedSegment}
        onOpenChange={() => setSelectedSegment(null)}
      >
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-2xl dark:text-gray-100">
              <Target className="h-6 w-6 text-blue-600" />
              {selectedSegment} Segment Analysis
            </DialogTitle>
          </DialogHeader>

          {segmentDrilldownLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="h-12 w-12 text-blue-600 mx-auto mb-4 animate-spin" />
                <p className="text-gray-600 dark:text-gray-400">
                  Loading segment details...
                </p>
              </div>
            </div>
          ) : segmentDrilldownData ? (
            <div className="space-y-6 mt-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <DollarSign className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      $
                      {segmentDrilldownData.total_spend.toLocaleString(
                        undefined,
                        { minimumFractionDigits: 0, maximumFractionDigits: 0 },
                      )}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Total Spend
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <Users className="h-8 w-8 mx-auto mb-2 text-green-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {segmentDrilldownData.supplier_count}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Suppliers
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <TrendingUp className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      $
                      {segmentDrilldownData.avg_spend_per_supplier.toLocaleString(
                        undefined,
                        { minimumFractionDigits: 0, maximumFractionDigits: 0 },
                      )}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Avg Spend/Supplier
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <Package className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {segmentDrilldownData.transaction_count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Transactions
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Supplier List Table */}
              <Card className="dark:bg-gray-700 dark:border-gray-600">
                <CardHeader>
                  <CardTitle className="text-lg dark:text-gray-100">
                    Supplier Details
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gray-800 text-white z-10">
                        <tr className="border-b-2 border-gray-300 dark:border-gray-600">
                          <th className="text-left p-3 font-semibold">Rank</th>
                          <th className="text-left p-3 font-semibold">
                            Supplier
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Total Spend
                          </th>
                          <th className="text-right p-3 font-semibold">
                            % of Segment
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Transactions
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Subcategories
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Locations
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {segmentDrilldownData.suppliers.map((supplier, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600/50"
                          >
                            <td className="p-3 text-gray-600 dark:text-gray-400">
                              {idx + 1}
                            </td>
                            <td className="p-3 font-medium text-gray-900 dark:text-gray-100">
                              {supplier.name}
                            </td>
                            <td className="p-3 text-right font-semibold text-gray-900 dark:text-gray-100">
                              $
                              {supplier.total_spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.percent_of_segment.toFixed(2)}%
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.transactions}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.subcategory_count}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.location_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Subcategory and Location Breakdown */}
              <div className="grid grid-cols-2 gap-6">
                {/* Top 10 Subcategories */}
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardHeader>
                    <CardTitle className="text-lg dark:text-gray-100">
                      Top 10 Subcategories
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {segmentDrilldownData.subcategories.map((item, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-900 dark:text-gray-100">
                              {item.name}
                            </span>
                            <span className="text-gray-600 dark:text-gray-400">
                              $
                              {item.spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}{" "}
                              ({item.percent_of_segment.toFixed(1)}%)
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{
                                width: `${Math.min(item.percent_of_segment, 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Top 10 Locations */}
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardHeader>
                    <CardTitle className="text-lg dark:text-gray-100">
                      Top 10 Locations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {segmentDrilldownData.locations.map((item, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-900 dark:text-gray-100">
                              {item.name}
                            </span>
                            <span className="text-gray-600 dark:text-gray-400">
                              $
                              {item.spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}{" "}
                              ({item.percent_of_segment.toFixed(1)}%)
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-purple-600 h-2 rounded-full"
                              style={{
                                width: `${Math.min(item.percent_of_segment, 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-12">
              <p className="text-gray-600 dark:text-gray-400">
                No data available for this segment.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Band Drill-Through Modal */}
      <Dialog open={!!selectedBand} onOpenChange={() => setSelectedBand(null)}>
        <DialogContent
          size="xl"
          className="max-h-[90vh] overflow-y-auto dark:bg-gray-800"
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-2xl dark:text-gray-100">
              <DollarSign className="h-6 w-6 text-blue-600" />
              {selectedBand} Spend Band Analysis
            </DialogTitle>
          </DialogHeader>

          {bandDrilldownLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="h-12 w-12 text-blue-600 mx-auto mb-4 animate-spin" />
                <p className="text-gray-600 dark:text-gray-400">
                  Loading spend band details...
                </p>
              </div>
            </div>
          ) : bandDrilldownData ? (
            <div className="space-y-6 mt-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <DollarSign className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      $
                      {bandDrilldownData.total_spend.toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0,
                      })}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Total Spend
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <Users className="h-8 w-8 mx-auto mb-2 text-green-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {bandDrilldownData.supplier_count}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Suppliers
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <TrendingUp className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      $
                      {bandDrilldownData.avg_spend_per_supplier.toLocaleString(
                        undefined,
                        { minimumFractionDigits: 0, maximumFractionDigits: 0 },
                      )}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Avg Spend/Supplier
                    </div>
                  </CardContent>
                </Card>

                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardContent className="pt-6 text-center">
                    <Package className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                      {bandDrilldownData.transaction_count.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Transactions
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Supplier List Table */}
              <Card className="dark:bg-gray-700 dark:border-gray-600">
                <CardHeader>
                  <CardTitle className="text-lg dark:text-gray-100">
                    Supplier Details
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gray-800 text-white z-10">
                        <tr className="border-b-2 border-gray-300 dark:border-gray-600">
                          <th className="text-left p-3 font-semibold">Rank</th>
                          <th className="text-left p-3 font-semibold">
                            Supplier
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Total Spend
                          </th>
                          <th className="text-right p-3 font-semibold">
                            % of Band
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Transactions
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Subcategories
                          </th>
                          <th className="text-right p-3 font-semibold">
                            Locations
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {bandDrilldownData.suppliers.map((supplier, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600/50"
                          >
                            <td className="p-3 text-gray-600 dark:text-gray-400">
                              {idx + 1}
                            </td>
                            <td className="p-3 font-medium text-gray-900 dark:text-gray-100">
                              {supplier.name}
                            </td>
                            <td className="p-3 text-right font-semibold text-gray-900 dark:text-gray-100">
                              $
                              {supplier.total_spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.percent_of_band.toFixed(2)}%
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.transactions}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.subcategory_count}
                            </td>
                            <td className="p-3 text-right text-gray-600 dark:text-gray-300">
                              {supplier.location_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Subcategory and Location Breakdown */}
              <div className="grid grid-cols-2 gap-6">
                {/* Top 10 Subcategories */}
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardHeader>
                    <CardTitle className="text-lg dark:text-gray-100">
                      Top 10 Subcategories
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {bandDrilldownData.subcategories.map((item, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-900 dark:text-gray-100">
                              {item.name}
                            </span>
                            <span className="text-gray-600 dark:text-gray-400">
                              $
                              {item.spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}{" "}
                              ({item.percent_of_band.toFixed(1)}%)
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{
                                width: `${Math.min(item.percent_of_band, 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Top 10 Locations */}
                <Card className="dark:bg-gray-700 dark:border-gray-600">
                  <CardHeader>
                    <CardTitle className="text-lg dark:text-gray-100">
                      Top 10 Locations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {bandDrilldownData.locations.map((item, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="font-medium text-gray-900 dark:text-gray-100">
                              {item.name}
                            </span>
                            <span className="text-gray-600 dark:text-gray-400">
                              $
                              {item.spend.toLocaleString(undefined, {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                              })}{" "}
                              ({item.percent_of_band.toFixed(1)}%)
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-purple-600 h-2 rounded-full"
                              style={{
                                width: `${Math.min(item.percent_of_band, 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-12">
              <p className="text-gray-600 dark:text-gray-400">
                No data available for this spend band.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
