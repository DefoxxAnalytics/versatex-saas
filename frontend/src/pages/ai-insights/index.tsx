/**
 * AI Insights Page
 *
 * Displays AI-powered procurement insights including:
 * - Cost optimization opportunities
 * - Supplier risk analysis
 * - Anomaly detection
 * - Consolidation recommendations
 */

import { useState, useMemo } from "react";
import {
  Sparkles,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  Users,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Target,
  Shield,
  Zap,
  RefreshCw,
  ArrowUpDown,
  CheckCircle,
  Clock,
  Flame,
  Brain,
  PlayCircle,
  XCircle,
  PauseCircle,
  Search,
  Layers,
  MessageSquare,
  Microscope,
  Loader2,
  BarChart3,
  History,
  Percent,
  TrendingDown,
  Filter,
  ChevronLeft,
  ChevronRight,
  Edit,
  Trash2,
  Cpu,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatCard } from "@/components/StatCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import { useSettings } from "@/hooks/useSettings";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useAIInsights,
  useRefreshAIInsights,
  useRecordInsightFeedback,
  useRequestAsyncEnhancement,
  useAsyncEnhancementStatus,
  useRequestDeepAnalysis,
  useDeepAnalysisStatus,
  useInsightEffectiveness,
  useInsightFeedbackList,
  useUpdateInsightOutcome,
  useDeleteInsightFeedback,
  filterInsightsByType,
  getInsightTypeLabel,
  getInsightTypeColor,
  getSeverityColor,
  getImpactColor,
  getEffortColor,
  getRiskLevelColor,
  sortRecommendationsByValue,
  getActionLabel,
  getActionColor,
  getOutcomeLabel,
  getOutcomeColor,
} from "@/hooks/useAIInsights";
import { DeepAnalysisModal } from "@/components/DeepAnalysisModal";
import { AIInsightsChat } from "@/components/AIInsightsChat";
import { LLMUsageDashboard } from "@/components/LLMUsageDashboard";
import type {
  AIInsight,
  AIInsightType,
  AIEnhancement,
  AIRecommendation,
  InsightActionTaken,
  InsightOutcome,
  PerInsightEnhancement,
  InsightFeedbackItem,
} from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";

// Sort options type
type SortOption = "savings" | "severity" | "confidence";

// Custom sort function based on selected option
function sortInsightsByOption(
  insights: AIInsight[],
  sortBy: SortOption,
): AIInsight[] {
  return [...insights].sort((a, b) => {
    switch (sortBy) {
      case "savings":
        return b.potential_savings - a.potential_savings;
      case "severity": {
        const severityOrder = { high: 0, medium: 1, low: 2 };
        return severityOrder[a.severity] - severityOrder[b.severity];
      }
      case "confidence":
        return b.confidence - a.confidence;
      default:
        return 0;
    }
  });
}

// Extended AIInsight type with per-insight enhancement
interface ExtendedAIInsight extends AIInsight {
  per_insight_enhancement?: PerInsightEnhancement;
}

// Insight card component
interface InsightCardProps {
  insight: ExtendedAIInsight;
  onRecordFeedback: (
    insight: AIInsight,
    action: InsightActionTaken,
    notes: string,
  ) => void;
  onDeepAnalysis: (insight: AIInsight) => void;
  isRecording?: boolean;
  isAnalyzing?: boolean;
  isAIConfigured?: boolean;
}

function InsightCard({
  insight,
  onRecordFeedback,
  onDeepAnalysis,
  isRecording,
  isAnalyzing,
  isAIConfigured,
}: InsightCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAIAnalysis, setShowAIAnalysis] = useState(false);
  const [showNotesDialog, setShowNotesDialog] = useState(false);
  const [selectedAction, setSelectedAction] =
    useState<InsightActionTaken | null>(null);
  const [actionNotes, setActionNotes] = useState("");

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getTypeIcon = (type: AIInsightType) => {
    const icons = {
      cost_optimization: DollarSign,
      risk: Shield,
      anomaly: Zap,
      consolidation: Users,
    };
    return icons[type] || Lightbulb;
  };

  const handleActionSelect = (action: InsightActionTaken) => {
    setSelectedAction(action);
    setShowNotesDialog(true);
  };

  const handleConfirmAction = () => {
    if (selectedAction) {
      onRecordFeedback(insight, selectedAction, actionNotes);
      setShowNotesDialog(false);
      setSelectedAction(null);
      setActionNotes("");
    }
  };

  const TypeIcon = getTypeIcon(insight.type);
  const hasAIEnhancement = !!insight.per_insight_enhancement;

  return (
    <>
      <Card className="hover:shadow-lg transition-shadow">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            {/* Type Icon */}
            <div
              className={`p-3 rounded-lg ${getInsightTypeColor(insight.type)}`}
            >
              <TypeIcon className="h-5 w-5" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-semibold text-gray-900 text-sm sm:text-base">
                  {insight.title}
                </h3>
                <div className="flex items-center gap-2 shrink-0">
                  {hasAIEnhancement && (
                    <Badge className="bg-purple-100 text-purple-800 border-purple-200 border text-xs">
                      <Brain className="h-3 w-3 mr-1" />
                      AI Analyzed
                    </Badge>
                  )}
                  <Badge
                    className={`${getSeverityColor(insight.severity)} border text-xs`}
                  >
                    {insight.severity.toUpperCase()}
                  </Badge>
                  {insight.potential_savings > 0 && (
                    <Badge className="bg-green-100 text-green-800 border-green-200 border text-xs">
                      {formatCurrency(insight.potential_savings)} savings
                    </Badge>
                  )}
                </div>
              </div>

              <p className="text-gray-600 text-sm mb-3">
                {insight.description}
              </p>

              {/* Confidence */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-gray-500">Confidence:</span>
                <div className="flex-1 max-w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${insight.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-600 font-medium">
                  {Math.round(insight.confidence * 100)}%
                </span>
              </div>

              {/* Action Buttons Row */}
              <div className="flex items-center gap-2 mb-3">
                {/* Expand/Collapse Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setExpanded(!expanded)}
                  className="text-blue-600 hover:text-blue-700"
                >
                  {expanded ? (
                    <>
                      <ChevronUp className="h-4 w-4 mr-1" />
                      Hide details
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-4 w-4 mr-1" />
                      Show details
                    </>
                  )}
                </Button>

                {/* AI Analysis Toggle */}
                {hasAIEnhancement && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAIAnalysis(!showAIAnalysis)}
                    className="text-purple-600 hover:text-purple-700"
                  >
                    <Brain className="h-4 w-4 mr-1" />
                    {showAIAnalysis ? "Hide" : "Show"} AI Analysis
                  </Button>
                )}

                {/* Deep Analysis Button */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDeepAnalysis(insight)}
                          disabled={isAnalyzing || !isAIConfigured}
                          className="text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
                        >
                          {isAnalyzing ? (
                            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          ) : (
                            <Microscope className="h-4 w-4 mr-1" />
                          )}
                          Deep Analysis
                        </Button>
                      </span>
                    </TooltipTrigger>
                    {!isAIConfigured && (
                      <TooltipContent>
                        <p>Enable External AI and add API key in Settings</p>
                      </TooltipContent>
                    )}
                  </Tooltip>
                </TooltipProvider>

                {/* Action Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={isRecording}
                      className="ml-auto"
                    >
                      <Layers className="h-4 w-4 mr-1" />
                      Take Action
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem
                      onClick={() => handleActionSelect("implemented")}
                    >
                      <PlayCircle className="h-4 w-4 mr-2 text-green-600" />
                      Implement
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleActionSelect("investigating")}
                    >
                      <Search className="h-4 w-4 mr-2 text-blue-600" />
                      Investigating
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleActionSelect("deferred")}
                    >
                      <PauseCircle className="h-4 w-4 mr-2 text-yellow-600" />
                      Defer for Later
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleActionSelect("partial")}
                    >
                      <Layers className="h-4 w-4 mr-2 text-purple-600" />
                      Partially Implement
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => handleActionSelect("dismissed")}
                    >
                      <XCircle className="h-4 w-4 mr-2 text-gray-600" />
                      Dismiss
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              {/* Per-Insight AI Analysis Section */}
              {showAIAnalysis && insight.per_insight_enhancement && (
                <div className="mb-4 p-4 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg border border-purple-100">
                  <h4 className="text-sm font-semibold text-purple-900 mb-3 flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    Detailed AI Analysis
                  </h4>

                  <p className="text-sm text-gray-700 mb-3">
                    {insight.per_insight_enhancement.analysis}
                  </p>

                  {insight.per_insight_enhancement.implementation_steps.length >
                    0 && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-purple-800 mb-1">
                        Implementation Steps:
                      </p>
                      <ol className="list-decimal list-inside space-y-1">
                        {insight.per_insight_enhancement.implementation_steps.map(
                          (step, i) => (
                            <li key={i} className="text-sm text-gray-600">
                              {step}
                            </li>
                          ),
                        )}
                      </ol>
                    </div>
                  )}

                  {insight.per_insight_enhancement.risk_factors.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-purple-800 mb-1">
                        Risk Factors:
                      </p>
                      <ul className="space-y-1">
                        {insight.per_insight_enhancement.risk_factors.map(
                          (risk, i) => (
                            <li
                              key={i}
                              className="text-sm text-gray-600 flex items-start gap-2"
                            >
                              <AlertTriangle className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />
                              {risk}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <div className="bg-white p-2 rounded border border-purple-100">
                      <span className="text-xs text-purple-600 font-medium">
                        Confidence:
                      </span>
                      <p className="text-gray-700">
                        {insight.per_insight_enhancement.confidence_rationale}
                      </p>
                    </div>
                    <div className="bg-white p-2 rounded border border-purple-100">
                      <span className="text-xs text-purple-600 font-medium">
                        Timeline:
                      </span>
                      <p className="text-gray-700">
                        {
                          insight.per_insight_enhancement
                            .timeline_recommendation
                        }
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Expanded Details */}
              {expanded && (
                <div className="mt-4 space-y-4 border-t pt-4">
                  {/* Recommended Actions */}
                  {insight.recommended_actions.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-2">
                        Recommended Actions
                      </h4>
                      <ul className="space-y-2">
                        {insight.recommended_actions.map((action, index) => (
                          <li
                            key={index}
                            className="flex items-start gap-2 text-sm text-gray-600"
                          >
                            <Target className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Affected Entities */}
                  {insight.affected_entities.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-2">
                        Affected Entities
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {insight.affected_entities.map((entity, index) => (
                          <Badge
                            key={index}
                            variant="outline"
                            className="text-xs"
                          >
                            {entity}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Additional Data */}
                  {insight.data && Object.keys(insight.data).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-2">
                        Details
                      </h4>
                      <div className="bg-gray-50 rounded-lg p-3 text-xs">
                        <pre className="whitespace-pre-wrap text-gray-600">
                          {JSON.stringify(insight.data, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notes Dialog */}
      <Dialog open={showNotesDialog} onOpenChange={setShowNotesDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedAction === "implemented" && (
                <PlayCircle className="h-5 w-5 text-green-600" />
              )}
              {selectedAction === "investigating" && (
                <Search className="h-5 w-5 text-blue-600" />
              )}
              {selectedAction === "deferred" && (
                <PauseCircle className="h-5 w-5 text-yellow-600" />
              )}
              {selectedAction === "partial" && (
                <Layers className="h-5 w-5 text-purple-600" />
              )}
              {selectedAction === "dismissed" && (
                <XCircle className="h-5 w-5 text-gray-600" />
              )}
              {selectedAction && getActionLabel(selectedAction)}
            </DialogTitle>
            <DialogDescription>
              Record your action on "{insight.title}"
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Add notes about your decision (optional)..."
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNotesDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirmAction} disabled={isRecording}>
              {isRecording ? "Recording..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Donut chart colors matching insight type colors
const CHART_COLORS = {
  cost_optimization: "#22c55e", // green
  risk: "#ef4444", // red
  anomaly: "#eab308", // yellow
  consolidation: "#3b82f6", // blue
};

// AI Recommendation Card Component
function RecommendationCard({
  recommendation,
  index,
}: {
  recommendation: AIRecommendation;
  index: number;
}) {
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="p-4 bg-white border border-indigo-100 rounded-lg hover:border-indigo-300 transition-colors">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
          <span className="text-sm font-bold text-indigo-600">{index + 1}</span>
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-sm font-medium text-gray-900">
            {recommendation.action}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={getImpactColor(recommendation.impact)}
            >
              {recommendation.impact} impact
            </Badge>
            <Badge
              variant="outline"
              className={getEffortColor(recommendation.effort)}
            >
              {recommendation.effort} effort
            </Badge>
            {recommendation.savings_estimate &&
              recommendation.savings_estimate > 0 && (
                <Badge
                  variant="outline"
                  className="bg-green-50 text-green-700 border-green-200"
                >
                  {formatCurrency(recommendation.savings_estimate)} est. savings
                </Badge>
              )}
            {recommendation.timeframe && (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                {recommendation.timeframe}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// AI Enhancement Section Component
function AIEnhancementSection({
  enhancement,
  cacheHit,
}: {
  enhancement: AIEnhancement;
  cacheHit?: boolean;
}) {
  const [showAllActions, setShowAllActions] = useState(false);
  const sortedActions = useMemo(
    () => sortRecommendationsByValue(enhancement.priority_actions),
    [enhancement.priority_actions],
  );
  const displayedActions = showAllActions
    ? sortedActions
    : sortedActions.slice(0, 3);

  return (
    <Card className="border-0 shadow-lg bg-gradient-to-br from-indigo-50 to-purple-50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-indigo-600" />
            <CardTitle className="text-indigo-900">
              AI Strategic Recommendations
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {cacheHit && (
              <Badge variant="outline" className="text-xs bg-white">
                Cached
              </Badge>
            )}
            <Badge variant="outline" className="text-xs bg-white">
              Powered by{" "}
              {enhancement.provider === "anthropic" ? "Claude" : "GPT-4"}
            </Badge>
          </div>
        </div>
        <CardDescription className="text-indigo-700">
          {enhancement.strategic_summary}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Quick Wins */}
        {enhancement.quick_wins && enhancement.quick_wins.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
              <Flame className="h-4 w-4 text-orange-500" />
              Quick Wins
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {enhancement.quick_wins.map((win, i) => (
                <div
                  key={i}
                  className="p-3 bg-white border border-orange-100 rounded-lg"
                >
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-orange-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {win.action}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {win.expected_benefit}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Priority Actions */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
            <Target className="h-4 w-4 text-indigo-600" />
            Priority Actions ({enhancement.priority_actions.length})
          </h4>
          <div className="space-y-2">
            {displayedActions.map((action, i) => (
              <RecommendationCard key={i} recommendation={action} index={i} />
            ))}
          </div>
          {sortedActions.length > 3 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAllActions(!showAllActions)}
              className="w-full text-indigo-600 hover:text-indigo-700"
            >
              {showAllActions
                ? "Show Less"
                : `Show ${sortedActions.length - 3} More`}
              {showAllActions ? (
                <ChevronUp className="h-4 w-4 ml-1" />
              ) : (
                <ChevronDown className="h-4 w-4 ml-1" />
              )}
            </Button>
          )}
        </div>

        {/* Risk Assessment */}
        {enhancement.risk_assessment && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
              <Shield className="h-4 w-4 text-red-500" />
              Risk Assessment
            </h4>
            <div className="p-4 bg-white border border-red-100 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  Overall Risk Level:
                </span>
                <Badge
                  className={getRiskLevelColor(
                    enhancement.risk_assessment.overall_risk_level,
                  )}
                >
                  {enhancement.risk_assessment.overall_risk_level}
                </Badge>
              </div>
              {enhancement.risk_assessment.key_risks &&
                enhancement.risk_assessment.key_risks.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-2">
                      Key Risks:
                    </p>
                    <ul className="space-y-1">
                      {enhancement.risk_assessment.key_risks.map((risk, i) => (
                        <li
                          key={i}
                          className="text-sm text-gray-700 flex items-start gap-2"
                        >
                          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                          {risk}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {enhancement.risk_assessment.mitigation_steps &&
                enhancement.risk_assessment.mitigation_steps.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-2">
                      Mitigation Steps:
                    </p>
                    <ul className="space-y-1">
                      {enhancement.risk_assessment.mitigation_steps.map(
                        (step, i) => (
                          <li
                            key={i}
                            className="text-sm text-gray-700 flex items-start gap-2"
                          >
                            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            {step}
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ROI Tracking Section Component
function ROITrackingSection() {
  const { data: effectiveness, isLoading: effectivenessLoading } =
    useInsightEffectiveness();
  const [feedbackFilters, setFeedbackFilters] = useState<{
    insight_type?: AIInsightType;
    action_taken?: InsightActionTaken;
    outcome?: InsightOutcome;
  }>({});
  const [feedbackPage, setFeedbackPage] = useState(0);
  const pageSize = 10;

  const {
    data: feedbackData,
    isLoading: feedbackLoading,
    refetch: refetchFeedback,
  } = useInsightFeedbackList({
    ...feedbackFilters,
    limit: pageSize,
    offset: feedbackPage * pageSize,
  });

  const updateOutcomeMutation = useUpdateInsightOutcome();
  const deleteFeedbackMutation = useDeleteInsightFeedback();

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [feedbackToDelete, setFeedbackToDelete] =
    useState<InsightFeedbackItem | null>(null);

  // Outcome update dialog state
  const [outcomeDialogOpen, setOutcomeDialogOpen] = useState(false);
  const [selectedFeedback, setSelectedFeedback] =
    useState<InsightFeedbackItem | null>(null);
  const [outcomeForm, setOutcomeForm] = useState<{
    outcome: InsightOutcome;
    actual_savings: string;
    outcome_notes: string;
  }>({
    outcome: "pending",
    actual_savings: "",
    outcome_notes: "",
  });

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const handleOpenOutcomeDialog = (feedback: InsightFeedbackItem) => {
    setSelectedFeedback(feedback);
    setOutcomeForm({
      outcome: feedback.outcome,
      actual_savings: feedback.actual_savings?.toString() || "",
      outcome_notes: feedback.outcome_notes || "",
    });
    setOutcomeDialogOpen(true);
  };

  const handleUpdateOutcome = () => {
    if (!selectedFeedback) return;

    updateOutcomeMutation.mutate(
      {
        feedbackId: selectedFeedback.id,
        data: {
          outcome: outcomeForm.outcome,
          actual_savings: outcomeForm.actual_savings
            ? parseFloat(outcomeForm.actual_savings)
            : undefined,
          outcome_notes: outcomeForm.outcome_notes || undefined,
        },
      },
      {
        onSuccess: () => {
          setOutcomeDialogOpen(false);
          setSelectedFeedback(null);
          refetchFeedback();
        },
      },
    );
  };

  const handleDeleteFeedback = () => {
    if (!feedbackToDelete) return;

    deleteFeedbackMutation.mutate(feedbackToDelete.id, {
      onSuccess: () => {
        setDeleteDialogOpen(false);
        setFeedbackToDelete(null);
        refetchFeedback();
      },
    });
  };

  const totalPages = feedbackData
    ? Math.ceil(feedbackData.total / pageSize)
    : 0;

  return (
    <div className="space-y-6">
      {/* Effectiveness Metrics Dashboard */}
      <Card className="border-0 shadow-lg bg-gradient-to-br from-emerald-50 to-teal-50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-emerald-600" />
            <CardTitle className="text-emerald-900">
              ROI & Effectiveness Metrics
            </CardTitle>
          </div>
          <CardDescription className="text-emerald-700">
            Track the impact and accuracy of AI-generated insights
          </CardDescription>
        </CardHeader>
        <CardContent>
          {effectivenessLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-white rounded-lg p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
                  <div className="h-8 bg-gray-200 rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : effectiveness?.total_feedback === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <History className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No feedback recorded yet</p>
              <p className="text-sm mt-1">
                Use "Take Action" on insights to start tracking ROI
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-emerald-100 rounded-lg">
                      <Target className="h-4 w-4 text-emerald-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      Total Actions
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {effectiveness?.total_feedback || 0}
                  </div>
                  <div className="text-xs text-gray-500">
                    insights acted upon
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      Success Rate
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {effectiveness?.implementation_success_rate?.toFixed(1) ||
                      0}
                    %
                  </div>
                  <div className="text-xs text-gray-500">
                    {effectiveness?.successful_implementations || 0} of{" "}
                    {effectiveness?.total_implemented || 0} successful
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <DollarSign className="h-4 w-4 text-blue-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      Actual Savings
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {formatCurrency(
                      effectiveness?.savings_metrics?.total_actual_savings || 0,
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    realized from implementations
                  </div>
                </div>

                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Percent className="h-4 w-4 text-purple-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      Prediction Accuracy
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900">
                    {effectiveness?.savings_metrics?.roi_accuracy_percent?.toFixed(
                      1,
                    ) || "N/A"}
                    {effectiveness?.savings_metrics?.roi_accuracy_percent
                      ? "%"
                      : ""}
                  </div>
                  <div className="text-xs text-gray-500">
                    actual vs predicted savings
                  </div>
                </div>
              </div>

              {/* Savings Comparison */}
              {(effectiveness?.savings_metrics?.total_predicted_savings || 0) >
                0 && (
                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">
                    Savings Comparison
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <div className="text-xs text-blue-600 font-medium mb-1">
                        Predicted
                      </div>
                      <div className="text-xl font-bold text-blue-800">
                        {formatCurrency(
                          effectiveness?.savings_metrics
                            ?.total_predicted_savings || 0,
                        )}
                      </div>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <div className="text-xs text-green-600 font-medium mb-1">
                        Actual
                      </div>
                      <div className="text-xl font-bold text-green-800">
                        {formatCurrency(
                          effectiveness?.savings_metrics
                            ?.total_actual_savings || 0,
                        )}
                      </div>
                    </div>
                    <div
                      className={`text-center p-3 rounded-lg ${
                        (effectiveness?.savings_metrics?.savings_variance ||
                          0) >= 0
                          ? "bg-green-50"
                          : "bg-red-50"
                      }`}
                    >
                      <div
                        className={`text-xs font-medium mb-1 ${
                          (effectiveness?.savings_metrics?.savings_variance ||
                            0) >= 0
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        Variance
                      </div>
                      <div
                        className={`text-xl font-bold flex items-center justify-center gap-1 ${
                          (effectiveness?.savings_metrics?.savings_variance ||
                            0) >= 0
                            ? "text-green-800"
                            : "text-red-800"
                        }`}
                      >
                        {(effectiveness?.savings_metrics?.savings_variance ||
                          0) >= 0 ? (
                          <TrendingUp className="h-5 w-5" />
                        ) : (
                          <TrendingDown className="h-5 w-5" />
                        )}
                        {formatCurrency(
                          Math.abs(
                            effectiveness?.savings_metrics?.savings_variance ||
                              0,
                          ),
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action & Outcome Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Action Breakdown */}
                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">
                    Actions Taken
                  </h4>
                  <div className="space-y-2">
                    {effectiveness?.action_breakdown?.map((item) => (
                      <div
                        key={item.action_taken}
                        className="flex items-center justify-between"
                      >
                        <Badge
                          className={`${getActionColor(item.action_taken)} border text-xs`}
                        >
                          {getActionLabel(item.action_taken)}
                        </Badge>
                        <span className="text-sm font-medium text-gray-700">
                          {item.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Outcome Breakdown */}
                <div className="bg-white rounded-lg p-4 shadow-sm border border-emerald-100">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">
                    Outcomes
                  </h4>
                  <div className="space-y-2">
                    {effectiveness?.outcome_breakdown?.length ? (
                      effectiveness.outcome_breakdown.map((item) => (
                        <div
                          key={item.outcome}
                          className="flex items-center justify-between"
                        >
                          <Badge
                            className={`${getOutcomeColor(item.outcome)} border text-xs`}
                          >
                            {getOutcomeLabel(item.outcome)}
                          </Badge>
                          <span className="text-sm font-medium text-gray-700">
                            {item.count}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">
                        No outcomes recorded yet
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Feedback History Panel */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-6 w-6 text-gray-600" />
              <CardTitle>Action History</CardTitle>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchFeedback()}
              disabled={feedbackLoading}
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${feedbackLoading ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </div>
          <CardDescription>
            Track actions taken on AI insights and update outcomes
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm text-gray-600">Filters:</span>
            </div>
            <Select
              value={feedbackFilters.insight_type || "all"}
              onValueChange={(v) => {
                setFeedbackFilters((f) => ({
                  ...f,
                  insight_type: v === "all" ? undefined : (v as AIInsightType),
                }));
                setFeedbackPage(0);
              }}
            >
              <SelectTrigger className="w-[140px] h-8">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="cost_optimization">Cost</SelectItem>
                <SelectItem value="risk">Risk</SelectItem>
                <SelectItem value="anomaly">Anomaly</SelectItem>
                <SelectItem value="consolidation">Consolidation</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={feedbackFilters.action_taken || "all"}
              onValueChange={(v) => {
                setFeedbackFilters((f) => ({
                  ...f,
                  action_taken:
                    v === "all" ? undefined : (v as InsightActionTaken),
                }));
                setFeedbackPage(0);
              }}
            >
              <SelectTrigger className="w-[140px] h-8">
                <SelectValue placeholder="Action" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="implemented">Implemented</SelectItem>
                <SelectItem value="investigating">Investigating</SelectItem>
                <SelectItem value="deferred">Deferred</SelectItem>
                <SelectItem value="partial">Partial</SelectItem>
                <SelectItem value="dismissed">Dismissed</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={feedbackFilters.outcome || "all"}
              onValueChange={(v) => {
                setFeedbackFilters((f) => ({
                  ...f,
                  outcome: v === "all" ? undefined : (v as InsightOutcome),
                }));
                setFeedbackPage(0);
              }}
            >
              <SelectTrigger className="w-[140px] h-8">
                <SelectValue placeholder="Outcome" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Outcomes</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="partial_success">Partial Success</SelectItem>
                <SelectItem value="no_change">No Change</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            {(feedbackFilters.insight_type ||
              feedbackFilters.action_taken ||
              feedbackFilters.outcome) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFeedbackFilters({});
                  setFeedbackPage(0);
                }}
                className="h-8 text-gray-500"
              >
                <XCircle className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>

          {/* Feedback List */}
          {feedbackLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 border rounded-lg animate-pulse">
                  <div className="flex justify-between">
                    <div className="h-5 bg-gray-200 rounded w-1/3" />
                    <div className="h-5 bg-gray-200 rounded w-20" />
                  </div>
                  <div className="h-4 bg-gray-200 rounded w-1/4 mt-2" />
                </div>
              ))}
            </div>
          ) : !feedbackData?.feedback?.length ? (
            <div className="text-center py-12 text-gray-500">
              <History className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No feedback history found</p>
              {(feedbackFilters.insight_type ||
                feedbackFilters.action_taken ||
                feedbackFilters.outcome) && (
                <p className="text-sm mt-1">Try adjusting your filters</p>
              )}
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {feedbackData.feedback.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 border rounded-lg hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-gray-900 truncate">
                          {item.insight_title}
                        </h4>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <Badge
                            className={`${getInsightTypeColor(item.insight_type)} text-xs`}
                          >
                            {getInsightTypeLabel(item.insight_type)}
                          </Badge>
                          <Badge
                            className={`${getSeverityColor(item.insight_severity)} border text-xs`}
                          >
                            {item.insight_severity}
                          </Badge>
                          <Badge
                            className={`${getActionColor(item.action_taken)} border text-xs`}
                          >
                            {getActionLabel(item.action_taken)}
                          </Badge>
                          <Badge
                            className={`${getOutcomeColor(item.outcome)} border text-xs`}
                          >
                            {getOutcomeLabel(item.outcome)}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(item.action_date)}
                          </span>
                          {item.predicted_savings &&
                            item.predicted_savings > 0 && (
                              <span className="flex items-center gap-1">
                                <DollarSign className="h-3 w-3" />
                                Predicted:{" "}
                                {formatCurrency(item.predicted_savings)}
                              </span>
                            )}
                          {item.actual_savings !== null &&
                            item.actual_savings !== undefined && (
                              <span className="flex items-center gap-1 text-green-600">
                                <CheckCircle className="h-3 w-3" />
                                Actual: {formatCurrency(item.actual_savings)}
                              </span>
                            )}
                          {item.action_by && <span>by {item.action_by}</span>}
                        </div>
                        {item.action_notes && (
                          <p className="text-sm text-gray-600 mt-2 italic">
                            "{item.action_notes}"
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenOutcomeDialog(item)}
                        >
                          <Edit className="h-4 w-4 mr-1" />
                          Update
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setFeedbackToDelete(item);
                            setDeleteDialogOpen(true);
                          }}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <span className="text-sm text-gray-500">
                    Showing {feedbackPage * pageSize + 1}-
                    {Math.min(
                      (feedbackPage + 1) * pageSize,
                      feedbackData.total,
                    )}{" "}
                    of {feedbackData.total}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setFeedbackPage((p) => Math.max(0, p - 1))}
                      disabled={feedbackPage === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-gray-600">
                      Page {feedbackPage + 1} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setFeedbackPage((p) => Math.min(totalPages - 1, p + 1))
                      }
                      disabled={feedbackPage >= totalPages - 1}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Update Outcome Dialog */}
      <Dialog open={outcomeDialogOpen} onOpenChange={setOutcomeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="h-5 w-5 text-blue-600" />
              Update Outcome
            </DialogTitle>
            <DialogDescription>
              Record the actual outcome of implementing this insight
            </DialogDescription>
          </DialogHeader>
          {selectedFeedback && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 text-sm">
                  {selectedFeedback.insight_title}
                </h4>
                <div className="flex items-center gap-2 mt-2">
                  <Badge
                    className={`${getActionColor(selectedFeedback.action_taken)} border text-xs`}
                  >
                    {getActionLabel(selectedFeedback.action_taken)}
                  </Badge>
                  {selectedFeedback.predicted_savings &&
                    selectedFeedback.predicted_savings > 0 && (
                      <span className="text-xs text-gray-500">
                        Predicted:{" "}
                        {formatCurrency(selectedFeedback.predicted_savings)}
                      </span>
                    )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="outcome">Outcome</Label>
                <Select
                  value={outcomeForm.outcome}
                  onValueChange={(v) =>
                    setOutcomeForm((f) => ({
                      ...f,
                      outcome: v as InsightOutcome,
                    }))
                  }
                >
                  <SelectTrigger id="outcome">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="partial_success">
                      Partial Success
                    </SelectItem>
                    <SelectItem value="no_change">No Change</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="actual_savings">Actual Savings ($)</Label>
                <Input
                  id="actual_savings"
                  type="number"
                  placeholder="0.00"
                  value={outcomeForm.actual_savings}
                  onChange={(e) =>
                    setOutcomeForm((f) => ({
                      ...f,
                      actual_savings: e.target.value,
                    }))
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="outcome_notes">Notes</Label>
                <Textarea
                  id="outcome_notes"
                  placeholder="Add notes about the outcome..."
                  value={outcomeForm.outcome_notes}
                  onChange={(e) =>
                    setOutcomeForm((f) => ({
                      ...f,
                      outcome_notes: e.target.value,
                    }))
                  }
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOutcomeDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpdateOutcome}
              disabled={updateOutcomeMutation.isPending}
            >
              {updateOutcomeMutation.isPending ? "Saving..." : "Save Outcome"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-red-600" />
              Delete Feedback Entry
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this feedback entry? This action
              cannot be undone.
              {feedbackToDelete && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium text-gray-900 text-sm">
                    {feedbackToDelete.insight_title}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge
                      className={`${getActionColor(feedbackToDelete.action_taken)} border text-xs`}
                    >
                      {getActionLabel(feedbackToDelete.action_taken)}
                    </Badge>
                    <span className="text-xs text-gray-500">
                      {formatDate(feedbackToDelete.action_date)}
                    </span>
                  </div>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setFeedbackToDelete(null)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteFeedback}
              className="bg-red-600 hover:bg-red-700 text-white"
              disabled={deleteFeedbackMutation.isPending}
            >
              {deleteFeedbackMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default function AIInsightsPage() {
  const { data, isLoading, error, refetch, isFetching } = useAIInsights();
  const refreshMutation = useRefreshAIInsights();
  const feedbackMutation = useRecordInsightFeedback();
  const { data: settings } = useSettings();
  const [mainView, setMainView] = useState<"insights" | "roi" | "chat" | "usage">("insights");
  const [activeTab, setActiveTab] = useState<AIInsightType | "all">("all");
  const [sortBy, setSortBy] = useState<SortOption>("severity");

  // Check if external AI is properly configured (enabled + API key)
  const isAIConfigured = settings?.useExternalAI && !!settings?.aiApiKey;

  // Deep Analysis state
  const [selectedInsightForAnalysis, setSelectedInsightForAnalysis] =
    useState<AIInsight | null>(null);
  const [deepAnalysisModalOpen, setDeepAnalysisModalOpen] = useState(false);
  const deepAnalysisMutation = useRequestDeepAnalysis();
  const { data: deepAnalysisStatus } = useDeepAnalysisStatus(
    selectedInsightForAnalysis?.id || null,
    deepAnalysisModalOpen,
  );

  // Async Enhancement state
  const asyncEnhancementMutation = useRequestAsyncEnhancement();
  const { data: asyncStatus } = useAsyncEnhancementStatus(
    asyncEnhancementMutation.isSuccess,
  );
  const isAsyncProcessing =
    asyncStatus?.status === "processing" || asyncStatus?.status === "queued";

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  const handleAsyncEnhance = () => {
    if (data?.insights) {
      asyncEnhancementMutation.mutate(data.insights);
    }
  };

  const handleDeepAnalysis = (insight: AIInsight) => {
    setSelectedInsightForAnalysis(insight);
    setDeepAnalysisModalOpen(true);
    deepAnalysisMutation.mutate(insight);
  };

  const handleCloseDeepAnalysis = () => {
    setDeepAnalysisModalOpen(false);
    setSelectedInsightForAnalysis(null);
  };

  const handleRecordFeedback = (
    insight: AIInsight,
    action: InsightActionTaken,
    notes: string,
  ) => {
    feedbackMutation.mutate({
      insight_id: insight.id,
      insight_type: insight.type,
      insight_title: insight.title,
      insight_severity: insight.severity,
      predicted_savings:
        insight.potential_savings > 0 ? insight.potential_savings : undefined,
      action_taken: action,
      action_notes: notes || undefined,
    });
  };

  const isRefreshing = isFetching || refreshMutation.isPending;

  // Filter and sort insights
  const filteredInsights = useMemo(() => {
    if (!data?.insights) return [];
    const filtered = filterInsightsByType(data.insights, activeTab);
    return sortInsightsByOption(filtered, sortBy);
  }, [data?.insights, activeTab, sortBy]);

  // Calculate savings by type for donut chart
  const savingsByType = useMemo(() => {
    if (!data?.insights) return [];
    const savingsMap: Record<string, number> = {};

    data.insights.forEach((insight) => {
      if (insight.potential_savings > 0) {
        savingsMap[insight.type] =
          (savingsMap[insight.type] || 0) + insight.potential_savings;
      }
    });

    return Object.entries(savingsMap).map(([type, value]) => ({
      name: getInsightTypeLabel(type as AIInsightType),
      value,
      type,
    }));
  }, [data?.insights]);

  // Format currency
  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-8 p-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-yellow-500" />
            AI Insights
          </h1>
          <p className="text-gray-600 mt-2">
            Smart recommendations powered by machine learning
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>

        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-gray-200 rounded-lg" />
                  <div className="flex-1 space-y-3">
                    <div className="h-5 bg-gray-200 rounded w-2/3" />
                    <div className="h-4 bg-gray-200 rounded w-full" />
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md">
          <AlertTriangle className="h-16 w-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Unable to Load Insights
          </h2>
          <p className="text-gray-600 mb-6">
            There was an error loading AI insights. This may be due to
            insufficient data or a server issue.
          </p>
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  // No data state
  if (!data || data.insights.length === 0) {
    return (
      <div className="space-y-8 p-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-yellow-500" />
            AI Insights
          </h1>
          <p className="text-gray-600 mt-2">
            Smart recommendations powered by machine learning
          </p>
        </div>

        <div className="flex items-center justify-center min-h-[300px]">
          <div className="text-center max-w-md">
            <Lightbulb className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              No Insights Available
            </h2>
            <p className="text-gray-600">
              Upload more procurement data to generate AI-powered insights and
              recommendations. The system needs sufficient transaction history
              to identify patterns and opportunities.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const { summary } = data;

  return (
    <div className="space-y-8 p-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-yellow-500" />
            AI Insights
          </h1>
          <p className="text-gray-600 mt-2">
            Smart recommendations powered by machine learning
          </p>
        </div>
        <div className="flex items-center gap-2">
          {mainView === "insights" && (
            <>
              {/* Async Enhancement Button */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Button
                        onClick={handleAsyncEnhance}
                        variant="outline"
                        disabled={
                          isAsyncProcessing ||
                          asyncEnhancementMutation.isPending ||
                          !data?.insights?.length ||
                          !isAIConfigured
                        }
                        className="border-purple-200 text-purple-700 hover:bg-purple-50 disabled:opacity-50"
                      >
                        {isAsyncProcessing ||
                        asyncEnhancementMutation.isPending ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {asyncStatus?.progress !== undefined
                              ? `${asyncStatus.progress}%`
                              : "Processing..."}
                          </>
                        ) : (
                          <>
                            <Brain className="h-4 w-4 mr-2" />
                            Enhance with AI
                          </>
                        )}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!isAIConfigured && (
                    <TooltipContent>
                      <p>Enable External AI and add API key in Settings</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>

              <Button
                onClick={handleRefresh}
                variant="outline"
                disabled={isRefreshing}
              >
                <RefreshCw
                  className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
                />
                {isRefreshing ? "Refreshing..." : "Refresh"}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Main View Tabs */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg w-fit">
        <Button
          variant={mainView === "insights" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMainView("insights")}
          className={mainView === "insights" ? "" : "text-gray-600"}
        >
          <Lightbulb className="h-4 w-4 mr-2" />
          Insights
        </Button>
        <Button
          variant={mainView === "roi" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMainView("roi")}
          className={mainView === "roi" ? "" : "text-gray-600"}
        >
          <BarChart3 className="h-4 w-4 mr-2" />
          ROI Tracking
        </Button>
        <Button
          variant={mainView === "chat" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMainView("chat")}
          className={mainView === "chat" ? "" : "text-gray-600"}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          AI Chat
        </Button>
        <Button
          variant={mainView === "usage" ? "default" : "ghost"}
          size="sm"
          onClick={() => setMainView("usage")}
          className={mainView === "usage" ? "" : "text-gray-600"}
        >
          <Cpu className="h-4 w-4 mr-2" />
          Usage
        </Button>
      </div>

      {/* Conditional View Rendering */}
      {mainView === "chat" ? (
        <AIInsightsChat />
      ) : mainView === "usage" ? (
        <LLMUsageDashboard />
      ) : mainView === "roi" ? (
        <ROITrackingSection />
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            <StatCard
              title="Total Insights"
              value={summary.total_insights}
              description="Recommendations found"
              icon={Lightbulb}
            />
            <StatCard
              title="High Priority"
              value={summary.high_priority}
              description="Require attention"
              icon={AlertTriangle}
              className={
                summary.high_priority > 0 ? "border-red-200 bg-red-50" : ""
              }
            />
            <StatCard
              title="Potential Savings"
              value={formatCurrency(summary.total_potential_savings)}
              description="Identified opportunities"
              icon={DollarSign}
              className="border-green-200 bg-green-50"
            />
            <StatCard
              title="Categories"
              value={Object.keys(summary.by_type).length}
              description="Insight types"
              icon={Target}
            />
          </div>

          {/* Savings Visualization and Insights Overview Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Savings by Type Donut Chart */}
            {savingsByType.length > 0 && (
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <DollarSign className="h-6 w-6 text-green-600" />
                    <CardTitle>Savings by Type</CardTitle>
                  </div>
                  <CardDescription>
                    Potential savings breakdown by insight category
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={savingsByType}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {savingsByType.map((entry) => (
                          <Cell
                            key={entry.type}
                            fill={
                              CHART_COLORS[
                                entry.type as keyof typeof CHART_COLORS
                              ] || "#94a3b8"
                            }
                          />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        formatter={(value: number) => formatCurrency(value)}
                        contentStyle={{
                          backgroundColor: "white",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                          boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                        }}
                      />
                      <Legend
                        verticalAlign="bottom"
                        height={36}
                        formatter={(value) => (
                          <span className="text-sm text-gray-600">{value}</span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="text-center mt-2">
                    <div className="text-2xl font-bold text-green-600">
                      {formatCurrency(summary.total_potential_savings)}
                    </div>
                    <div className="text-sm text-gray-500">
                      Total Potential Savings
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Insights by Type Summary - spans 2 columns on lg screens */}
            <Card
              className={`border-0 shadow-lg bg-gradient-to-br from-yellow-50 to-amber-50 ${savingsByType.length > 0 ? "lg:col-span-2" : "lg:col-span-3"}`}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-6 w-6 text-amber-600" />
                  <CardTitle className="text-amber-900">
                    Insights Overview
                  </CardTitle>
                </div>
                <CardDescription className="text-amber-700">
                  AI-powered analysis of your procurement data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg p-4 shadow-sm border border-amber-100">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <DollarSign className="h-4 w-4 text-green-600" />
                      </div>
                      <span className="text-sm font-medium text-gray-700">
                        Cost
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                      {summary.by_type.cost_optimization || 0}
                    </div>
                    <div className="text-xs text-gray-500">
                      optimization opportunities
                    </div>
                  </div>

                  <div className="bg-white rounded-lg p-4 shadow-sm border border-amber-100">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 bg-red-100 rounded-lg">
                        <Shield className="h-4 w-4 text-red-600" />
                      </div>
                      <span className="text-sm font-medium text-gray-700">
                        Risk
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                      {summary.by_type.risk || 0}
                    </div>
                    <div className="text-xs text-gray-500">
                      supplier risks identified
                    </div>
                  </div>

                  <div className="bg-white rounded-lg p-4 shadow-sm border border-amber-100">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 bg-yellow-100 rounded-lg">
                        <Zap className="h-4 w-4 text-yellow-600" />
                      </div>
                      <span className="text-sm font-medium text-gray-700">
                        Anomalies
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                      {summary.by_type.anomaly || 0}
                    </div>
                    <div className="text-xs text-gray-500">
                      unusual patterns detected
                    </div>
                  </div>

                  <div className="bg-white rounded-lg p-4 shadow-sm border border-amber-100">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Users className="h-4 w-4 text-blue-600" />
                      </div>
                      <span className="text-sm font-medium text-gray-700">
                        Consolidation
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                      {summary.by_type.consolidation || 0}
                    </div>
                    <div className="text-xs text-gray-500">
                      consolidation opportunities
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* AI Strategic Recommendations */}
          {data.ai_enhancement && (
            <AIEnhancementSection
              enhancement={data.ai_enhancement}
              cacheHit={data.cache_hit}
            />
          )}

          {/* Insights List with Tabs */}
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <CardTitle>Detailed Insights</CardTitle>
                  <CardDescription>
                    Click on each insight to see recommended actions and
                    affected entities
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <ArrowUpDown className="h-4 w-4 text-gray-500" />
                  <Select
                    value={sortBy}
                    onValueChange={(v) => setSortBy(v as SortOption)}
                  >
                    <SelectTrigger className="w-[160px]">
                      <SelectValue placeholder="Sort by" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="severity">Severity</SelectItem>
                      <SelectItem value="savings">Savings Potential</SelectItem>
                      <SelectItem value="confidence">Confidence</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs
                value={activeTab}
                onValueChange={(v) => setActiveTab(v as AIInsightType | "all")}
              >
                <TabsList className="mb-6">
                  <TabsTrigger value="all">
                    All ({data.insights.length})
                  </TabsTrigger>
                  <TabsTrigger value="cost_optimization">
                    Cost ({summary.by_type.cost_optimization || 0})
                  </TabsTrigger>
                  <TabsTrigger value="risk">
                    Risk ({summary.by_type.risk || 0})
                  </TabsTrigger>
                  <TabsTrigger value="anomaly">
                    Anomalies ({summary.by_type.anomaly || 0})
                  </TabsTrigger>
                  <TabsTrigger value="consolidation">
                    Consolidation ({summary.by_type.consolidation || 0})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value={activeTab} className="mt-0">
                  {filteredInsights.length > 0 ? (
                    <div className="space-y-4">
                      {filteredInsights.map((insight) => (
                        <InsightCard
                          key={insight.id}
                          insight={insight as ExtendedAIInsight}
                          onRecordFeedback={handleRecordFeedback}
                          onDeepAnalysis={handleDeepAnalysis}
                          isRecording={feedbackMutation.isPending}
                          isAnalyzing={
                            deepAnalysisMutation.isPending &&
                            selectedInsightForAnalysis?.id === insight.id
                          }
                          isAIConfigured={isAIConfigured}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-500">
                      <Lightbulb className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                      <p>
                        No {getInsightTypeLabel(activeTab as AIInsightType)}{" "}
                        insights found
                      </p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Deep Analysis Modal */}
          <DeepAnalysisModal
            open={deepAnalysisModalOpen}
            onClose={handleCloseDeepAnalysis}
            insight={selectedInsightForAnalysis}
            status={deepAnalysisStatus?.status || null}
            progress={deepAnalysisStatus?.progress || 0}
            analysis={deepAnalysisStatus?.analysis || null}
            error={deepAnalysisStatus?.error}
            onRequestAnalysis={() => {
              if (selectedInsightForAnalysis) {
                deepAnalysisMutation.mutate(selectedInsightForAnalysis);
              }
            }}
            isRequesting={deepAnalysisMutation.isPending}
          />
        </>
      )}
    </div>
  );
}
