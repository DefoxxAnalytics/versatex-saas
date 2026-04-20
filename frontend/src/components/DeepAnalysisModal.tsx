/**
 * DeepAnalysisModal Component
 *
 * A modal that displays comprehensive AI-powered deep analysis for an insight.
 * Shows root cause analysis, implementation roadmap, financial impact, risks, and more.
 */

import { useState } from "react";
import {
  X,
  ChevronRight,
  AlertTriangle,
  DollarSign,
  Users,
  Target,
  Clock,
  CheckCircle2,
  Loader2,
  TrendingUp,
  Shield,
  Lightbulb,
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
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AIInsight } from "@/lib/api";
import type {
  DeepAnalysis,
  DeepAnalysisStatus,
  DeepAnalysisRiskFactor,
} from "@/hooks/useAIInsights";
import { getDeepAnalysisRiskColor, getPhaseColor } from "@/hooks/useAIInsights";

interface DeepAnalysisModalProps {
  open: boolean;
  onClose: () => void;
  insight: AIInsight | null;
  status: DeepAnalysisStatus | null;
  progress: number;
  analysis: DeepAnalysis | null;
  error?: string;
  onRequestAnalysis: () => void;
  isRequesting: boolean;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function RiskBadge({
  likelihood,
  impact,
}: {
  likelihood: "high" | "medium" | "low";
  impact: "high" | "medium" | "low";
}) {
  const colorClass = getDeepAnalysisRiskColor(likelihood, impact);
  const riskLevel =
    likelihood === "high" && impact === "high"
      ? "Critical"
      : likelihood === "high" || impact === "high"
        ? "High"
        : likelihood === "medium" || impact === "medium"
          ? "Medium"
          : "Low";
  return (
    <Badge variant="outline" className={colorClass}>
      {riskLevel}
    </Badge>
  );
}

export function DeepAnalysisModal({
  open,
  onClose,
  insight,
  status,
  progress,
  analysis,
  error,
  onRequestAnalysis,
  isRequesting,
}: DeepAnalysisModalProps) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!insight) return null;

  const renderLoadingState = () => (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
      <div className="text-center">
        <p className="text-lg font-medium">Analyzing Insight...</p>
        <p className="text-sm text-muted-foreground mt-1">
          {status === "processing"
            ? `Processing... ${progress}%`
            : "Queued for analysis"}
        </p>
      </div>
      <Progress value={progress} className="w-64" />
    </div>
  );

  const renderErrorState = () => (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <AlertTriangle className="h-12 w-12 text-red-500" />
      <div className="text-center">
        <p className="text-lg font-medium text-red-600">Analysis Failed</p>
        <p className="text-sm text-muted-foreground mt-1">
          {error || "An error occurred during analysis"}
        </p>
      </div>
      <button
        onClick={onRequestAnalysis}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        disabled={isRequesting}
      >
        Try Again
      </button>
    </div>
  );

  const renderNotStartedState = () => (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <Lightbulb className="h-12 w-12 text-amber-500" />
      <div className="text-center max-w-md">
        <p className="text-lg font-medium">Deep Analysis Available</p>
        <p className="text-sm text-muted-foreground mt-2">
          Get comprehensive analysis including root cause investigation,
          implementation roadmap, financial impact assessment, and risk factors.
        </p>
      </div>
      <button
        onClick={onRequestAnalysis}
        className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-md hover:from-blue-700 hover:to-indigo-700 flex items-center gap-2"
        disabled={isRequesting}
      >
        {isRequesting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Starting Analysis...
          </>
        ) : (
          <>
            <Target className="h-4 w-4" />
            Start Deep Analysis
          </>
        )}
      </button>
    </div>
  );

  const renderAnalysis = () => {
    if (!analysis) return null;

    return (
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="roadmap">Roadmap</TabsTrigger>
          <TabsTrigger value="financial">Financial</TabsTrigger>
          <TabsTrigger value="risks">Risks</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 mt-4">
          {/* Executive Summary */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                Executive Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{analysis.executive_summary}</p>
            </CardContent>
          </Card>

          {/* Root Cause Analysis */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Target className="h-4 w-4 text-red-500" />
                Root Cause Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase">
                  Primary Cause
                </p>
                <p className="text-sm mt-1">
                  {analysis.root_cause_analysis.primary_cause}
                </p>
              </div>
              {analysis.root_cause_analysis.contributing_factors &&
                analysis.root_cause_analysis.contributing_factors.length >
                  0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">
                      Contributing Factors
                    </p>
                    <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                      {analysis.root_cause_analysis.contributing_factors.map(
                        (factor, i) => (
                          <li key={i}>{factor}</li>
                        ),
                      )}
                    </ul>
                  </div>
                )}
              {analysis.root_cause_analysis.systemic_issues &&
                analysis.root_cause_analysis.systemic_issues.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">
                      Systemic Issues
                    </p>
                    <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                      {analysis.root_cause_analysis.systemic_issues.map(
                        (issue, i) => (
                          <li key={i}>{issue}</li>
                        ),
                      )}
                    </ul>
                  </div>
                )}
            </CardContent>
          </Card>

          {/* Next Steps */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                Immediate Next Steps
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="list-decimal list-inside text-sm space-y-2">
                {analysis.next_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </CardContent>
          </Card>

          {/* Industry Context */}
          {analysis.industry_context && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-blue-500" />
                  Industry Context
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {analysis.industry_context.benchmark && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">
                      Benchmark
                    </p>
                    <p className="text-sm mt-1">
                      {analysis.industry_context.benchmark}
                    </p>
                  </div>
                )}
                {analysis.industry_context.best_practices &&
                  analysis.industry_context.best_practices.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase">
                        Best Practices
                      </p>
                      <ul className="list-disc list-inside text-sm mt-1 space-y-1">
                        {analysis.industry_context.best_practices.map(
                          (practice, i) => (
                            <li key={i}>{practice}</li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="roadmap" className="space-y-4 mt-4">
          <div className="space-y-4">
            {analysis.implementation_roadmap.map((phase, index) => (
              <Card key={index} className="relative overflow-hidden">
                <div
                  className={`absolute left-0 top-0 bottom-0 w-1 ${getPhaseColor(index, analysis.implementation_roadmap.length).split(" ")[0]}`}
                />
                <CardHeader className="pb-2 pl-5">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={getPhaseColor(
                          index,
                          analysis.implementation_roadmap.length,
                        )}
                      >
                        Phase {phase.phase}
                      </Badge>
                      {phase.title}
                    </CardTitle>
                    {phase.duration && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {phase.duration}
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pl-5 space-y-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase">
                      Tasks
                    </p>
                    <ul className="text-sm mt-1 space-y-1">
                      {phase.tasks.map((task, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                          {task}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {phase.deliverables && phase.deliverables.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase">
                        Deliverables
                      </p>
                      <ul className="text-sm mt-1 space-y-1">
                        {phase.deliverables.map((deliverable, i) => (
                          <li key={i} className="flex items-center gap-2">
                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                            {deliverable}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {phase.dependencies && phase.dependencies.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase">
                        Dependencies
                      </p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {phase.dependencies.map((dep, i) => (
                          <Badge
                            key={i}
                            variant="secondary"
                            className="text-xs"
                          >
                            {dep}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="financial" className="space-y-4 mt-4">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-4">
            {analysis.financial_impact.estimated_savings && (
              <Card className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950 dark:to-emerald-950">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                    <DollarSign className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">
                      Estimated Savings
                    </span>
                  </div>
                  <p className="text-2xl font-bold mt-1">
                    {formatCurrency(
                      analysis.financial_impact.estimated_savings,
                    )}
                  </p>
                </CardContent>
              </Card>
            )}
            {analysis.financial_impact.implementation_cost && (
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <DollarSign className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">
                      Implementation Cost
                    </span>
                  </div>
                  <p className="text-2xl font-bold mt-1">
                    {formatCurrency(
                      analysis.financial_impact.implementation_cost,
                    )}
                  </p>
                </CardContent>
              </Card>
            )}
            {analysis.financial_impact.payback_period && (
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">
                      Payback Period
                    </span>
                  </div>
                  <p className="text-2xl font-bold mt-1">
                    {analysis.financial_impact.payback_period}
                  </p>
                </CardContent>
              </Card>
            )}
            {analysis.financial_impact.roi_percentage && (
              <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase">
                      Expected ROI
                    </span>
                  </div>
                  <p className="text-2xl font-bold mt-1">
                    {analysis.financial_impact.roi_percentage}%
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Savings Breakdown */}
          {analysis.financial_impact.savings_breakdown &&
            analysis.financial_impact.savings_breakdown.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    Savings Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analysis.financial_impact.savings_breakdown.map(
                      (item, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between border-b pb-2 last:border-0"
                        >
                          <div>
                            <p className="text-sm font-medium">
                              {item.category}
                            </p>
                            {item.description && (
                              <p className="text-xs text-muted-foreground">
                                {item.description}
                              </p>
                            )}
                          </div>
                          <span className="font-semibold text-green-600">
                            {formatCurrency(item.amount)}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
        </TabsContent>

        <TabsContent value="risks" className="space-y-4 mt-4">
          {analysis.risk_factors && analysis.risk_factors.length > 0 ? (
            <div className="space-y-3">
              {analysis.risk_factors.map((risk: DeepAnalysisRiskFactor, i) => (
                <Card key={i}>
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <Shield className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">{risk.risk}</p>
                          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                            <span>
                              Likelihood:{" "}
                              <span className="capitalize">
                                {risk.likelihood}
                              </span>
                            </span>
                            <span>|</span>
                            <span>
                              Impact:{" "}
                              <span className="capitalize">{risk.impact}</span>
                            </span>
                          </div>
                        </div>
                      </div>
                      <RiskBadge
                        likelihood={risk.likelihood}
                        impact={risk.impact}
                      />
                    </div>
                    <div className="mt-3 pl-8">
                      <p className="text-xs font-medium text-muted-foreground uppercase">
                        Mitigation
                      </p>
                      <p className="text-sm mt-1">{risk.mitigation}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No significant risks identified</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4 mt-4">
          {/* Success Metrics */}
          {analysis.success_metrics && analysis.success_metrics.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Target className="h-4 w-4 text-green-500" />
                  Success Metrics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analysis.success_metrics.map((metric, i) => (
                    <div
                      key={i}
                      className="border-b pb-3 last:border-0 last:pb-0"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          {metric.metric}
                        </span>
                        <Badge
                          variant="outline"
                          className="bg-green-50 text-green-700 border-green-200"
                        >
                          Target: {metric.target}
                        </Badge>
                      </div>
                      {metric.measurement_method && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Measurement: {metric.measurement_method}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stakeholders */}
          {analysis.stakeholders && analysis.stakeholders.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  Key Stakeholders
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.stakeholders.map((stakeholder, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center shrink-0">
                        <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {stakeholder.role}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {stakeholder.responsibility}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    );
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="flex items-center justify-between pr-8">
            <span>Deep Analysis: {insight.title}</span>
            {analysis && (
              <Badge variant="outline" className="ml-2 text-xs">
                {analysis.provider === "anthropic" ? "Claude" : "GPT-4"}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 -mx-6 px-6">
          {status === "not_found" || !status
            ? renderNotStartedState()
            : status === "processing"
              ? renderLoadingState()
              : status === "failed"
                ? renderErrorState()
                : status === "completed" && analysis
                  ? renderAnalysis()
                  : renderNotStartedState()}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
