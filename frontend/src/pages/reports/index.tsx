/**
 * Reports Module - Main Page
 *
 * Provides report generation, history, and scheduling functionality
 * with a tabbed interface.
 */
import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import {
  FileText,
  PieChart,
  Users,
  BarChart2,
  Shield,
  TrendingDown,
  Download,
  Clock,
  Calendar,
  Trash2,
  Eye,
  Share2,
  PlayCircle,
  Loader2,
  FileSpreadsheet,
  FileType2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Plus,
  Edit2,
  ChevronDown,
  Filter,
  DollarSign,
  Layers,
  CalendarDays,
  TrendingUp,
  Scissors,
  // P2P Report icons
  FileCheck,
  ShieldCheck,
  ClipboardList,
} from "lucide-react";
import { useSuppliers, useCategories } from "@/hooks/useAnalytics";
import {
  useReportTemplates,
  useReportHistory,
  useReportSchedules,
  useGenerateReport,
  useDeleteReport,
  useDownloadReport,
  useReportStatus,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useRunScheduleNow,
  useReportPreview,
} from "@/hooks/useReports";
import {
  ReportTemplate,
  ReportListItem,
  ReportType,
  ReportFormat,
  ReportStatus,
  ScheduleFrequency,
  ReportScheduleRequest,
  ReportPreviewData,
} from "@/lib/api";
import { SkeletonCard } from "@/components/SkeletonCard";

// Icon mapping for report types
const REPORT_ICONS: Record<string, React.ElementType> = {
  executive_summary: FileText,
  spend_analysis: PieChart,
  supplier_performance: Users,
  pareto_analysis: BarChart2,
  contract_compliance: Shield,
  savings_opportunities: TrendingDown,
  price_trends: TrendingDown,
  stratification: Layers,
  seasonality: CalendarDays,
  year_over_year: TrendingUp,
  tail_spend: Scissors,
  custom: FileText,
  // P2P Report icons
  p2p_pr_status: FileCheck,
  p2p_po_compliance: ShieldCheck,
  p2p_ap_aging: Clock,
};

// Color themes for each report type (gradient backgrounds and accent colors)
const REPORT_THEMES: Record<
  string,
  { gradient: string; iconBg: string; iconColor: string; hoverBorder: string }
> = {
  executive_summary: {
    gradient: "from-violet-500/10 via-violet-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-violet-500 to-purple-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-violet-400",
  },
  spend_analysis: {
    gradient: "from-blue-500/10 via-blue-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-blue-500 to-cyan-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-blue-400",
  },
  supplier_performance: {
    gradient: "from-emerald-500/10 via-emerald-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-emerald-500 to-teal-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-emerald-400",
  },
  pareto_analysis: {
    gradient: "from-amber-500/10 via-amber-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-amber-500 to-orange-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-amber-400",
  },
  contract_compliance: {
    gradient: "from-rose-500/10 via-rose-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-rose-500 to-pink-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-rose-400",
  },
  savings_opportunities: {
    gradient: "from-green-500/10 via-green-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-green-500 to-emerald-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-green-400",
  },
  price_trends: {
    gradient: "from-indigo-500/10 via-indigo-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-indigo-500 to-purple-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-indigo-400",
  },
  stratification: {
    gradient: "from-sky-500/10 via-sky-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-sky-500 to-blue-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-sky-400",
  },
  seasonality: {
    gradient: "from-teal-500/10 via-teal-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-teal-500 to-cyan-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-teal-400",
  },
  year_over_year: {
    gradient: "from-fuchsia-500/10 via-fuchsia-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-fuchsia-500 to-pink-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-fuchsia-400",
  },
  tail_spend: {
    gradient: "from-orange-500/10 via-orange-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-orange-500 to-red-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-orange-400",
  },
  custom: {
    gradient: "from-slate-500/10 via-slate-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-slate-500 to-gray-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-slate-400",
  },
  // P2P Report themes - teal/cyan family for distinctive P2P look
  p2p_pr_status: {
    gradient: "from-teal-500/10 via-teal-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-teal-500 to-emerald-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-teal-400",
  },
  p2p_po_compliance: {
    gradient: "from-cyan-500/10 via-cyan-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-cyan-500 to-teal-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-cyan-400",
  },
  p2p_ap_aging: {
    gradient: "from-sky-500/10 via-sky-500/5 to-transparent",
    iconBg: "bg-gradient-to-br from-sky-600 to-cyan-600",
    iconColor: "text-white",
    hoverBorder: "hover:border-sky-400",
  },
};

// Report categories for grouping
const REPORT_CATEGORIES: Record<
  string,
  { title: string; description: string; types: string[] }
> = {
  executive: {
    title: "Executive & Overview",
    description: "High-level insights and strategic summaries",
    types: ["executive_summary", "spend_analysis"],
  },
  supplier: {
    title: "Supplier Intelligence",
    description: "Vendor analysis, performance, and relationships",
    types: ["supplier_performance", "pareto_analysis", "tail_spend"],
  },
  trends: {
    title: "Trends & Patterns",
    description: "Historical analysis and forecasting",
    types: ["seasonality", "year_over_year", "price_trends"],
  },
  optimization: {
    title: "Optimization & Compliance",
    description: "Savings opportunities and policy adherence",
    types: ["savings_opportunities", "contract_compliance", "stratification"],
  },
  p2p: {
    title: "P2P Analytics",
    description: "Procure-to-Pay workflow and performance metrics",
    types: ["p2p_pr_status", "p2p_po_compliance", "p2p_ap_aging"],
  },
};

// Badges for special reports
const REPORT_BADGES: Record<
  string,
  { label: string; variant: "new" | "popular" | "recommended" }
> = {
  stratification: { label: "New", variant: "new" },
  seasonality: { label: "New", variant: "new" },
  year_over_year: { label: "New", variant: "new" },
  tail_spend: { label: "New", variant: "new" },
  executive_summary: { label: "Popular", variant: "popular" },
  spend_analysis: { label: "Recommended", variant: "recommended" },
  // P2P Report badges
  p2p_pr_status: { label: "New", variant: "new" },
  p2p_po_compliance: { label: "New", variant: "new" },
  p2p_ap_aging: { label: "New", variant: "new" },
};

// Badge styles
const BADGE_STYLES: Record<string, string> = {
  new: "bg-gradient-to-r from-emerald-500 to-teal-500 text-white",
  popular: "bg-gradient-to-r from-amber-500 to-orange-500 text-white",
  recommended: "bg-gradient-to-r from-blue-500 to-indigo-500 text-white",
};

// Status badge colors
const STATUS_COLORS: Record<ReportStatus, string> = {
  draft: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
  generating:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  scheduled: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
};

// Format icons
const FORMAT_ICONS: Record<ReportFormat, React.ElementType> = {
  pdf: FileText,
  xlsx: FileSpreadsheet,
  csv: FileType2,
};

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState("generate");
  const [selectedTemplate, setSelectedTemplate] =
    useState<ReportTemplate | null>(null);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [generatingReportId, setGeneratingReportId] = useState<string | null>(
    null,
  );

  // Form state for generation
  const [reportName, setReportName] = useState("");
  const [reportDescription, setReportDescription] = useState("");
  const [reportFormat, setReportFormat] = useState<ReportFormat>("pdf");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  // Advanced filters state
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<number[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");

  // Preview dialog state
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState<ReportPreviewData | null>(
    null,
  );

  // Schedule dialog state
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ReportListItem | null>(
    null,
  );
  const [scheduleName, setScheduleName] = useState("");
  const [scheduleReportType, setScheduleReportType] =
    useState<ReportType>("spend_analysis");
  const [scheduleFormat, setScheduleFormat] = useState<ReportFormat>("pdf");
  const [scheduleFrequency, setScheduleFrequency] =
    useState<ScheduleFrequency>("weekly");

  // Queries
  const { data: templates = [], isLoading: templatesLoading } =
    useReportTemplates();
  const {
    data: historyData,
    isLoading: historyLoading,
    refetch: refetchHistory,
  } = useReportHistory({ limit: 50 });
  const {
    data: schedules = [],
    isLoading: schedulesLoading,
    refetch: refetchSchedules,
  } = useReportSchedules();
  const { data: suppliers } = useSuppliers();
  const { data: categories } = useCategories();

  // Poll for status when generating
  const { data: reportStatus } = useReportStatus(
    generatingReportId,
    !!generatingReportId,
  );

  // Mutations
  const generateReport = useGenerateReport();
  const deleteReport = useDeleteReport();
  const downloadReport = useDownloadReport();
  const createSchedule = useCreateSchedule();
  const updateSchedule = useUpdateSchedule();
  const deleteSchedule = useDeleteSchedule();
  const runScheduleNow = useRunScheduleNow();
  const reportPreview = useReportPreview();

  // Effect to handle generation completion
  useEffect(() => {
    if (reportStatus?.status === "completed") {
      toast.success("Report generated successfully");
      setGeneratingReportId(null);
      refetchHistory();
    } else if (reportStatus?.status === "failed") {
      toast.error(
        `Report generation failed: ${reportStatus.error_message || "Unknown error"}`,
      );
      setGeneratingReportId(null);
      refetchHistory();
    }
  }, [reportStatus?.status]);

  const handleGenerateClick = (template: ReportTemplate) => {
    setSelectedTemplate(template);
    setReportName(`${template.name} - ${new Date().toLocaleDateString()}`);
    setReportDescription("");
    setReportFormat("pdf");
    setPeriodStart("");
    setPeriodEnd("");
    // Reset advanced filters
    setFiltersOpen(false);
    setSelectedSupplierIds([]);
    setSelectedCategoryIds([]);
    setMinAmount("");
    setMaxAmount("");
    setGenerateDialogOpen(true);
  };

  // Build filters object from current state
  const buildFilters = () => {
    const filters: Record<string, unknown> = {};
    if (selectedSupplierIds.length > 0) {
      filters.supplier_ids = selectedSupplierIds;
    }
    if (selectedCategoryIds.length > 0) {
      filters.category_ids = selectedCategoryIds;
    }
    if (minAmount) {
      filters.min_amount = parseFloat(minAmount);
    }
    if (maxAmount) {
      filters.max_amount = parseFloat(maxAmount);
    }
    return Object.keys(filters).length > 0 ? filters : undefined;
  };

  const handlePreview = async () => {
    if (!selectedTemplate) return;

    try {
      const data = await reportPreview.mutateAsync({
        report_type: selectedTemplate.report_type,
        report_format: reportFormat,
        name: reportName,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
        filters: buildFilters(),
      });
      setPreviewData(data);
      setGenerateDialogOpen(false);
      setPreviewDialogOpen(true);
    } catch (error) {
      toast.error("Failed to generate preview");
    }
  };

  const handleGenerateFromPreview = async () => {
    if (!selectedTemplate) return;

    try {
      const result = await generateReport.mutateAsync({
        report_type: selectedTemplate.report_type,
        report_format: reportFormat,
        name: reportName,
        description: reportDescription,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
        filters: buildFilters(),
        async_generation: true,
      });

      setPreviewDialogOpen(false);
      setPreviewData(null);

      if ("message" in result && result.id) {
        setGeneratingReportId(result.id);
        toast.info("Report generation started. This may take a moment...");
        setActiveTab("history");
      } else {
        toast.success("Report generated successfully");
        refetchHistory();
        setActiveTab("history");
      }
    } catch (error) {
      toast.error("Failed to generate report");
    }
  };

  const handleGenerate = async () => {
    if (!selectedTemplate) return;

    try {
      const result = await generateReport.mutateAsync({
        report_type: selectedTemplate.report_type,
        report_format: reportFormat,
        name: reportName,
        description: reportDescription,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
        filters: buildFilters(),
        async_generation: true,
      });

      setGenerateDialogOpen(false);

      if ("message" in result && result.id) {
        // Async generation started
        setGeneratingReportId(result.id);
        toast.info("Report generation started. This may take a moment...");
        setActiveTab("history");
      } else {
        // Sync generation completed
        toast.success("Report generated successfully");
        refetchHistory();
        setActiveTab("history");
      }
    } catch (error) {
      toast.error("Failed to generate report");
    }
  };

  const handleDownload = async (report: ReportListItem) => {
    try {
      await downloadReport.mutateAsync({
        reportId: report.id,
        format: report.report_format,
        filename: `${report.name}.${report.report_format}`,
      });
      toast.success("Download started");
    } catch (error) {
      toast.error("Failed to download report");
    }
  };

  const handleDelete = async (reportId: string) => {
    if (!confirm("Are you sure you want to delete this report?")) return;

    try {
      await deleteReport.mutateAsync(reportId);
      toast.success("Report deleted");
    } catch (error) {
      toast.error("Failed to delete report");
    }
  };

  const handleRunSchedule = async (scheduleId: string) => {
    try {
      await runScheduleNow.mutateAsync(scheduleId);
      toast.success("Report generation triggered");
      refetchHistory();
    } catch (error) {
      toast.error("Failed to trigger report");
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (!confirm("Are you sure you want to delete this schedule?")) return;

    try {
      await deleteSchedule.mutateAsync(scheduleId);
      toast.success("Schedule deleted");
    } catch (error) {
      toast.error("Failed to delete schedule");
    }
  };

  const handleOpenScheduleDialog = (schedule?: ReportListItem) => {
    if (schedule) {
      // Editing existing schedule
      setEditingSchedule(schedule);
      setScheduleName(schedule.name);
      setScheduleReportType(schedule.report_type);
      setScheduleFormat(schedule.report_format);
      setScheduleFrequency(
        (schedule.schedule_frequency as ScheduleFrequency) || "weekly",
      );
    } else {
      // Creating new schedule
      setEditingSchedule(null);
      setScheduleName("");
      setScheduleReportType("spend_analysis");
      setScheduleFormat("pdf");
      setScheduleFrequency("weekly");
    }
    setScheduleDialogOpen(true);
  };

  const handleSaveSchedule = async () => {
    if (!scheduleName.trim()) {
      toast.error("Please enter a schedule name");
      return;
    }

    try {
      const scheduleData: ReportScheduleRequest = {
        name: scheduleName,
        report_type: scheduleReportType,
        report_format: scheduleFormat,
        is_scheduled: true,
        schedule_frequency: scheduleFrequency,
      };

      if (editingSchedule) {
        await updateSchedule.mutateAsync({
          scheduleId: editingSchedule.id,
          data: scheduleData,
        });
        toast.success("Schedule updated");
      } else {
        await createSchedule.mutateAsync(scheduleData);
        toast.success("Schedule created");
      }

      setScheduleDialogOpen(false);
      refetchSchedules();
    } catch (error) {
      toast.error(
        editingSchedule
          ? "Failed to update schedule"
          : "Failed to create schedule",
      );
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString();
  };

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString();
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground mt-1">
            Generate, schedule, and manage procurement reports
          </p>
        </div>
        {generatingReportId && (
          <Badge variant="outline" className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating report...
          </Badge>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full max-w-[400px] grid-cols-3">
          <TabsTrigger value="generate" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Generate
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            History
          </TabsTrigger>
          <TabsTrigger value="schedules" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Schedules
          </TabsTrigger>
        </TabsList>

        {/* Generate Tab */}
        <TabsContent value="generate" className="mt-6">
          {templatesLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : (
            <div className="space-y-8">
              {Object.entries(REPORT_CATEGORIES).map(
                ([categoryKey, category]) => {
                  // Filter templates that belong to this category
                  const categoryTemplates = templates.filter((t) =>
                    category.types.includes(t.report_type),
                  );

                  if (categoryTemplates.length === 0) return null;

                  return (
                    <div key={categoryKey} className="space-y-4">
                      {/* Category Header */}
                      <div className="border-b pb-2">
                        <h3 className="text-lg font-semibold tracking-tight">
                          {category.title}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {category.description}
                        </p>
                      </div>

                      {/* Category Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {categoryTemplates.map((template) => {
                          const Icon =
                            REPORT_ICONS[template.report_type] || FileText;
                          const theme =
                            REPORT_THEMES[template.report_type] ||
                            REPORT_THEMES["custom"];
                          const badge = REPORT_BADGES[template.report_type];

                          return (
                            <Card
                              key={template.id}
                              className={`cursor-pointer group relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/20 hover:-translate-y-1 ${theme.hoverBorder}`}
                              onClick={() => handleGenerateClick(template)}
                            >
                              {/* Gradient Background */}
                              <div
                                className={`absolute inset-0 bg-gradient-to-br ${theme.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                              />

                              {/* Badge */}
                              {badge && (
                                <div className="absolute top-3 right-3 z-10">
                                  <span
                                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shadow-sm ${BADGE_STYLES[badge.variant]}`}
                                  >
                                    {badge.label}
                                  </span>
                                </div>
                              )}

                              <CardHeader className="relative z-10 pb-2">
                                <div className="flex items-start gap-4">
                                  {/* Icon with gradient background */}
                                  <div
                                    className={`p-3 rounded-xl ${theme.iconBg} shadow-lg shadow-black/10 group-hover:scale-110 transition-transform duration-300`}
                                  >
                                    <Icon
                                      className={`h-6 w-6 ${theme.iconColor}`}
                                    />
                                  </div>
                                  <div className="flex-1 min-w-0 pt-1">
                                    <CardTitle className="text-base font-semibold leading-tight group-hover:text-primary transition-colors">
                                      {template.name}
                                    </CardTitle>
                                  </div>
                                </div>
                              </CardHeader>
                              <CardContent className="relative z-10 pt-0">
                                <CardDescription className="text-sm leading-relaxed line-clamp-2">
                                  {template.description}
                                </CardDescription>

                                {/* Hover indicator */}
                                <div className="mt-4 flex items-center text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                  <span>Click to generate</span>
                                  <svg
                                    className="ml-1 h-3 w-3 group-hover:translate-x-1 transition-transform"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                </div>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </div>
                  );
                },
              )}

              {/* Uncategorized reports (if any) */}
              {(() => {
                const categorizedTypes = Object.values(
                  REPORT_CATEGORIES,
                ).flatMap((c) => c.types);
                const uncategorizedTemplates = templates.filter(
                  (t) =>
                    !categorizedTypes.includes(t.report_type) &&
                    t.report_type !== "custom",
                );

                if (uncategorizedTemplates.length === 0) return null;

                return (
                  <div className="space-y-4">
                    <div className="border-b pb-2">
                      <h3 className="text-lg font-semibold tracking-tight">
                        Other Reports
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Additional report types
                      </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {uncategorizedTemplates.map((template) => {
                        const Icon =
                          REPORT_ICONS[template.report_type] || FileText;
                        const theme =
                          REPORT_THEMES[template.report_type] ||
                          REPORT_THEMES["custom"];
                        const badge = REPORT_BADGES[template.report_type];

                        return (
                          <Card
                            key={template.id}
                            className={`cursor-pointer group relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/20 hover:-translate-y-1 ${theme.hoverBorder}`}
                            onClick={() => handleGenerateClick(template)}
                          >
                            <div
                              className={`absolute inset-0 bg-gradient-to-br ${theme.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                            />
                            {badge && (
                              <div className="absolute top-3 right-3 z-10">
                                <span
                                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shadow-sm ${BADGE_STYLES[badge.variant]}`}
                                >
                                  {badge.label}
                                </span>
                              </div>
                            )}
                            <CardHeader className="relative z-10 pb-2">
                              <div className="flex items-start gap-4">
                                <div
                                  className={`p-3 rounded-xl ${theme.iconBg} shadow-lg shadow-black/10 group-hover:scale-110 transition-transform duration-300`}
                                >
                                  <Icon
                                    className={`h-6 w-6 ${theme.iconColor}`}
                                  />
                                </div>
                                <div className="flex-1 min-w-0 pt-1">
                                  <CardTitle className="text-base font-semibold leading-tight group-hover:text-primary transition-colors">
                                    {template.name}
                                  </CardTitle>
                                </div>
                              </div>
                            </CardHeader>
                            <CardContent className="relative z-10 pt-0">
                              <CardDescription className="text-sm leading-relaxed line-clamp-2">
                                {template.description}
                              </CardDescription>
                              <div className="mt-4 flex items-center text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                <span>Click to generate</span>
                                <svg
                                  className="ml-1 h-3 w-3 group-hover:translate-x-1 transition-transform"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 5l7 7-7 7"
                                  />
                                </svg>
                              </div>
                            </CardContent>
                          </Card>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="mt-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-t-lg border-b">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  Report History
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {historyData?.results.length || 0} reports generated
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchHistory()}
                className="shadow-sm"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {historyLoading ? (
                <div className="p-6 space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-20 bg-gradient-to-r from-muted/50 to-muted animate-pulse rounded-lg"
                    />
                  ))}
                </div>
              ) : historyData?.results.length === 0 ? (
                <div className="text-center py-16 px-6">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 mb-4">
                    <FileText className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="font-semibold text-lg mb-1">No reports yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Generate your first report to see it here
                  </p>
                  <Button
                    onClick={() => setActiveTab("generate")}
                    className="shadow-sm"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Generate Report
                  </Button>
                </div>
              ) : (
                <div className="divide-y">
                  {historyData?.results.map((report) => {
                    const FormatIcon =
                      FORMAT_ICONS[report.report_format] || FileText;
                    const theme =
                      REPORT_THEMES[report.report_type] ||
                      REPORT_THEMES["custom"];
                    const ReportTypeIcon =
                      REPORT_ICONS[report.report_type] || FileText;
                    return (
                      <div
                        key={report.id}
                        className="group flex items-center justify-between p-4 hover:bg-gradient-to-r hover:from-slate-50/50 hover:to-transparent dark:hover:from-slate-800/50 transition-all duration-200"
                      >
                        <div className="flex items-center gap-4">
                          {/* Report Type Icon with Theme Color */}
                          <div
                            className={`p-2.5 rounded-xl ${theme.iconBg} shadow-md group-hover:scale-105 transition-transform`}
                          >
                            <ReportTypeIcon
                              className={`h-5 w-5 ${theme.iconColor}`}
                            />
                          </div>
                          <div className="min-w-0">
                            <div className="font-semibold text-sm truncate max-w-[200px] md:max-w-[300px] group-hover:text-primary transition-colors">
                              {report.name}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                              <span className="font-medium">
                                {report.report_type_display}
                              </span>
                              <span>•</span>
                              <span>
                                {formatDateTime(
                                  report.generated_at || report.created_at,
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {/* Format Badge */}
                          <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-medium">
                            <FormatIcon className="h-3.5 w-3.5" />
                            <span className="uppercase">
                              {report.report_format}
                            </span>
                          </div>
                          {/* Status Badge */}
                          <Badge
                            className={`${STATUS_COLORS[report.status]} shadow-sm`}
                          >
                            {report.status === "generating" && (
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                            )}
                            {report.status === "completed" && (
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                            )}
                            {report.status === "failed" && (
                              <XCircle className="h-3 w-3 mr-1" />
                            )}
                            {report.status_display}
                          </Badge>
                          {/* File Size */}
                          <span className="hidden md:inline text-xs text-muted-foreground font-mono">
                            {formatFileSize(report.file_size)}
                          </span>
                          {/* Actions */}
                          <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                            {report.status === "completed" && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 hover:bg-primary/10 hover:text-primary"
                                onClick={() => handleDownload(report)}
                                disabled={downloadReport.isPending}
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                              onClick={() => handleDelete(report.id)}
                              disabled={deleteReport.isPending}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Schedules Tab */}
        <TabsContent value="schedules" className="mt-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950 dark:to-purple-950 rounded-t-lg border-b">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                  Scheduled Reports
                </CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {schedules.length} active schedule
                  {schedules.length !== 1 ? "s" : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchSchedules()}
                  className="shadow-sm"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleOpenScheduleDialog()}
                  className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Schedule
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {schedulesLoading ? (
                <div className="p-6 space-y-4">
                  {[1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-24 bg-gradient-to-r from-muted/50 to-muted animate-pulse rounded-lg"
                    />
                  ))}
                </div>
              ) : schedules.length === 0 ? (
                <div className="text-center py-16 px-6">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900 dark:to-purple-900 mb-4">
                    <Calendar className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <h3 className="font-semibold text-lg mb-1">
                    No schedules yet
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Automate your report generation with schedules
                  </p>
                  <Button
                    onClick={() => handleOpenScheduleDialog()}
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-sm"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Your First Schedule
                  </Button>
                </div>
              ) : (
                <div className="divide-y">
                  {schedules.map((schedule) => {
                    const theme =
                      REPORT_THEMES[schedule.report_type] ||
                      REPORT_THEMES["custom"];
                    const ReportTypeIcon =
                      REPORT_ICONS[schedule.report_type] || FileText;
                    const frequencyColors: Record<string, string> = {
                      daily:
                        "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
                      weekly:
                        "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
                      bi_weekly:
                        "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
                      monthly:
                        "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
                      quarterly:
                        "bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300",
                    };
                    return (
                      <div
                        key={schedule.id}
                        className="group flex items-center justify-between p-4 hover:bg-gradient-to-r hover:from-indigo-50/50 hover:to-transparent dark:hover:from-indigo-950/50 transition-all duration-200"
                      >
                        <div className="flex items-center gap-4">
                          {/* Report Type Icon */}
                          <div
                            className={`p-2.5 rounded-xl ${theme.iconBg} shadow-md group-hover:scale-105 transition-transform`}
                          >
                            <ReportTypeIcon
                              className={`h-5 w-5 ${theme.iconColor}`}
                            />
                          </div>
                          <div className="min-w-0">
                            <div className="font-semibold text-sm truncate max-w-[200px] md:max-w-[300px] group-hover:text-primary transition-colors">
                              {schedule.name}
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-muted-foreground">
                                {schedule.report_type_display}
                              </span>
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${frequencyColors[schedule.schedule_frequency as string] || "bg-gray-100 text-gray-700"}`}
                              >
                                {schedule.schedule_frequency
                                  ?.replace("_", "-")
                                  .toUpperCase()}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {/* Next Run Info */}
                          <div className="text-right hidden sm:block">
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                              Next Run
                            </div>
                            <div className="text-sm font-medium">
                              {formatDateTime(schedule.next_run)}
                            </div>
                          </div>
                          {/* Actions */}
                          <div className="flex gap-0.5">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 hover:bg-green-100 hover:text-green-700 dark:hover:bg-green-900 dark:hover:text-green-300"
                              onClick={() => handleRunSchedule(schedule.id)}
                              disabled={runScheduleNow.isPending}
                              title="Run now"
                            >
                              <PlayCircle className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 hover:bg-blue-100 hover:text-blue-700 dark:hover:bg-blue-900 dark:hover:text-blue-300"
                              onClick={() => handleOpenScheduleDialog(schedule)}
                              title="Edit schedule"
                            >
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                              onClick={() => handleDeleteSchedule(schedule.id)}
                              disabled={deleteSchedule.isPending}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Generate Dialog */}
      <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Generate {selectedTemplate?.name}</DialogTitle>
            <DialogDescription>
              Configure your report options below. You can preview the data
              before generating the full report.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Report Name</Label>
              <Input
                id="name"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Enter report name"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                value={reportDescription}
                onChange={(e) => setReportDescription(e.target.value)}
                placeholder="Enter description"
                rows={2}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="format">Output Format</Label>
              <Select
                value={reportFormat}
                onValueChange={(v) => setReportFormat(v as ReportFormat)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF Document</SelectItem>
                  <SelectItem value="xlsx">Excel Spreadsheet</SelectItem>
                  <SelectItem value="csv">CSV File</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="start">Start Date (optional)</Label>
                <Input
                  id="start"
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="end">End Date (optional)</Label>
                <Input
                  id="end"
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                />
              </div>
            </div>

            {/* Advanced Filters */}
            <Collapsible open={filtersOpen} onOpenChange={setFiltersOpen}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  className="w-full justify-between px-0 hover:bg-transparent"
                >
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Filter className="h-4 w-4" />
                    Advanced Filters
                    {(selectedSupplierIds.length > 0 ||
                      selectedCategoryIds.length > 0 ||
                      minAmount ||
                      maxAmount) && (
                      <Badge variant="secondary" className="ml-2">
                        {selectedSupplierIds.length +
                          selectedCategoryIds.length +
                          (minAmount ? 1 : 0) +
                          (maxAmount ? 1 : 0)}{" "}
                        active
                      </Badge>
                    )}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${filtersOpen ? "rotate-180" : ""}`}
                  />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-4 pt-2">
                {/* Suppliers Filter */}
                <div className="grid gap-2">
                  <Label className="text-sm">Filter by Suppliers</Label>
                  <ScrollArea className="h-[120px] rounded-md border p-2">
                    <div className="space-y-2">
                      {!suppliers?.results || suppliers.results.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No suppliers available
                        </p>
                      ) : (
                        suppliers.results.slice(0, 20).map((supplier) => (
                          <div
                            key={supplier.id}
                            className="flex items-center space-x-2"
                          >
                            <Checkbox
                              id={`supplier-${supplier.id}`}
                              checked={selectedSupplierIds.includes(
                                supplier.id,
                              )}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedSupplierIds([
                                    ...selectedSupplierIds,
                                    supplier.id,
                                  ]);
                                } else {
                                  setSelectedSupplierIds(
                                    selectedSupplierIds.filter(
                                      (id) => id !== supplier.id,
                                    ),
                                  );
                                }
                              }}
                            />
                            <label
                              htmlFor={`supplier-${supplier.id}`}
                              className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                            >
                              {supplier.name}
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                  {selectedSupplierIds.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto py-1 px-2 text-xs"
                      onClick={() => setSelectedSupplierIds([])}
                    >
                      Clear ({selectedSupplierIds.length} selected)
                    </Button>
                  )}
                </div>

                {/* Categories Filter */}
                <div className="grid gap-2">
                  <Label className="text-sm">Filter by Categories</Label>
                  <ScrollArea className="h-[100px] rounded-md border p-2">
                    <div className="space-y-2">
                      {!categories?.results ||
                      categories.results.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No categories available
                        </p>
                      ) : (
                        categories.results.map((category) => (
                          <div
                            key={category.id}
                            className="flex items-center space-x-2"
                          >
                            <Checkbox
                              id={`category-${category.id}`}
                              checked={selectedCategoryIds.includes(
                                category.id,
                              )}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedCategoryIds([
                                    ...selectedCategoryIds,
                                    category.id,
                                  ]);
                                } else {
                                  setSelectedCategoryIds(
                                    selectedCategoryIds.filter(
                                      (id) => id !== category.id,
                                    ),
                                  );
                                }
                              }}
                            />
                            <label
                              htmlFor={`category-${category.id}`}
                              className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                            >
                              {category.name}
                            </label>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                  {selectedCategoryIds.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto py-1 px-2 text-xs"
                      onClick={() => setSelectedCategoryIds([])}
                    >
                      Clear ({selectedCategoryIds.length} selected)
                    </Button>
                  )}
                </div>

                {/* Amount Range Filter */}
                <div className="grid gap-2">
                  <Label className="text-sm flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    Amount Range
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Input
                        type="number"
                        placeholder="Min amount"
                        value={minAmount}
                        onChange={(e) => setMinAmount(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                    <div>
                      <Input
                        type="number"
                        placeholder="Max amount"
                        value={maxAmount}
                        onChange={(e) => setMaxAmount(e.target.value)}
                        min="0"
                        step="100"
                      />
                    </div>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setGenerateDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={handlePreview}
              disabled={reportPreview.isPending || generateReport.isPending}
            >
              {reportPreview.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  Preview
                </>
              )}
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={generateReport.isPending || reportPreview.isPending}
            >
              {generateReport.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Report
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editingSchedule ? "Edit Schedule" : "Create Schedule"}
            </DialogTitle>
            <DialogDescription>
              {editingSchedule
                ? "Update the settings for this scheduled report."
                : "Set up automatic report generation on a recurring schedule."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="schedule-name">Schedule Name</Label>
              <Input
                id="schedule-name"
                value={scheduleName}
                onChange={(e) => setScheduleName(e.target.value)}
                placeholder="e.g., Weekly Spend Report"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="schedule-report-type">Report Type</Label>
              <Select
                value={scheduleReportType}
                onValueChange={(v) => setScheduleReportType(v as ReportType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="spend_analysis">Spend Analysis</SelectItem>
                  <SelectItem value="supplier_performance">
                    Supplier Performance
                  </SelectItem>
                  <SelectItem value="executive_summary">
                    Executive Summary
                  </SelectItem>
                  <SelectItem value="pareto_analysis">
                    Pareto Analysis
                  </SelectItem>
                  <SelectItem value="contract_compliance">
                    Contract Compliance
                  </SelectItem>
                  <SelectItem value="savings_opportunities">
                    Savings Opportunities
                  </SelectItem>
                  <SelectItem value="price_trends">Price Trends</SelectItem>
                  <SelectItem value="stratification">
                    Spend Stratification
                  </SelectItem>
                  <SelectItem value="seasonality">
                    Seasonality & Trends
                  </SelectItem>
                  <SelectItem value="year_over_year">
                    Year-over-Year Analysis
                  </SelectItem>
                  <SelectItem value="tail_spend">
                    Tail Spend Analysis
                  </SelectItem>
                  <SelectItem value="p2p_pr_status">
                    PR Status Report
                  </SelectItem>
                  <SelectItem value="p2p_po_compliance">
                    PO Compliance Report
                  </SelectItem>
                  <SelectItem value="p2p_ap_aging">AP Aging Report</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="schedule-format">Output Format</Label>
              <Select
                value={scheduleFormat}
                onValueChange={(v) => setScheduleFormat(v as ReportFormat)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF Document</SelectItem>
                  <SelectItem value="xlsx">Excel Spreadsheet</SelectItem>
                  <SelectItem value="csv">CSV File</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="schedule-frequency">Frequency</Label>
              <Select
                value={scheduleFrequency}
                onValueChange={(v) =>
                  setScheduleFrequency(v as ScheduleFrequency)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="bi_weekly">Bi-Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="quarterly">Quarterly</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                Reports will be automatically generated on this schedule
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setScheduleDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveSchedule}
              disabled={createSchedule.isPending || updateSchedule.isPending}
            >
              {createSchedule.isPending || updateSchedule.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Calendar className="h-4 w-4 mr-2" />
                  {editingSchedule ? "Update Schedule" : "Create Schedule"}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onOpenChange={(open) => {
          setPreviewDialogOpen(open);
          if (!open) setPreviewData(null);
        }}
      >
        <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Report Preview: {selectedTemplate?.name}
            </DialogTitle>
            <DialogDescription>
              Review the report data preview below. Click "Generate Full Report"
              to create the complete report.
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="flex-1 pr-4">
            <div className="space-y-6 py-4">
              {/* Metadata Section */}
              {previewData?.metadata && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
                    Report Info
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">
                        Organization:
                      </span>
                      <span className="font-medium">
                        {previewData.metadata.organization}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Period:</span>
                      <span className="font-medium">
                        {previewData.metadata.period_start} -{" "}
                        {previewData.metadata.period_end}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Overview KPIs */}
              {previewData?.overview && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
                    Key Metrics
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {previewData.overview.total_spend !== undefined && (
                      <Card className="p-3">
                        <div className="text-xs text-muted-foreground">
                          Total Spend
                        </div>
                        <div className="text-lg font-bold text-primary">
                          $
                          {Number(
                            previewData.overview.total_spend,
                          ).toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </div>
                      </Card>
                    )}
                    {previewData.overview.transaction_count !== undefined && (
                      <Card className="p-3">
                        <div className="text-xs text-muted-foreground">
                          Transactions
                        </div>
                        <div className="text-lg font-bold">
                          {Number(
                            previewData.overview.transaction_count,
                          ).toLocaleString()}
                        </div>
                      </Card>
                    )}
                    {previewData.overview.supplier_count !== undefined && (
                      <Card className="p-3">
                        <div className="text-xs text-muted-foreground">
                          Suppliers
                        </div>
                        <div className="text-lg font-bold">
                          {previewData.overview.supplier_count}
                        </div>
                      </Card>
                    )}
                    {previewData.overview.category_count !== undefined && (
                      <Card className="p-3">
                        <div className="text-xs text-muted-foreground">
                          Categories
                        </div>
                        <div className="text-lg font-bold">
                          {previewData.overview.category_count}
                        </div>
                      </Card>
                    )}
                    {previewData.overview.avg_transaction !== undefined && (
                      <Card className="p-3">
                        <div className="text-xs text-muted-foreground">
                          Avg Transaction
                        </div>
                        <div className="text-lg font-bold">
                          $
                          {Number(
                            previewData.overview.avg_transaction,
                          ).toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </div>
                      </Card>
                    )}
                  </div>
                </div>
              )}

              {/* Spend by Category */}
              {previewData?.spend_by_category &&
                previewData.spend_by_category.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
                      Top Categories {previewData._truncated && "(Preview)"}
                    </h4>
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium">
                              Category
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              Amount
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              %
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewData.spend_by_category.map((item, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="px-3 py-2">{item.category}</td>
                              <td className="px-3 py-2 text-right">
                                $
                                {Number(item.amount).toLocaleString(undefined, {
                                  maximumFractionDigits: 0,
                                })}
                              </td>
                              <td className="px-3 py-2 text-right text-muted-foreground">
                                {Number(item.percentage).toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

              {/* Spend by Supplier */}
              {previewData?.spend_by_supplier &&
                previewData.spend_by_supplier.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
                      Top Suppliers {previewData._truncated && "(Preview)"}
                    </h4>
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium">
                              Supplier
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              Amount
                            </th>
                            <th className="px-3 py-2 text-right font-medium">
                              %
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewData.spend_by_supplier.map((item, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="px-3 py-2">{item.supplier}</td>
                              <td className="px-3 py-2 text-right">
                                $
                                {Number(item.amount).toLocaleString(undefined, {
                                  maximumFractionDigits: 0,
                                })}
                              </td>
                              <td className="px-3 py-2 text-right text-muted-foreground">
                                {Number(item.percentage).toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

              {/* Truncation notice */}
              {previewData?._truncated && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
                  <AlertCircle className="h-4 w-4" />
                  <span>
                    This preview shows a limited dataset. Generate the full
                    report for complete data.
                  </span>
                </div>
              )}
            </div>
          </ScrollArea>
          <DialogFooter className="border-t pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setPreviewDialogOpen(false);
                setPreviewData(null);
              }}
            >
              Close
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setPreviewDialogOpen(false);
                setGenerateDialogOpen(true);
              }}
            >
              <Edit2 className="h-4 w-4 mr-2" />
              Edit Options
            </Button>
            <Button
              onClick={handleGenerateFromPreview}
              disabled={generateReport.isPending}
            >
              {generateReport.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Full Report
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
