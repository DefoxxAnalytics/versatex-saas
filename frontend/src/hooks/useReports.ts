/**
 * Custom hooks for the Reports module.
 *
 * Provides TanStack Query hooks for report generation, listing,
 * downloading, and scheduling.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  reportsAPI,
  getOrganizationParam,
  ReportType,
  ReportStatus,
  ReportFormat,
  ReportGenerateRequest,
  ReportScheduleRequest,
  ReportShareRequest,
  ReportPreviewData,
} from "@/lib/api";

/**
 * Get the current organization ID for query key inclusion.
 */
function getOrgKeyPart(): number | undefined {
  const param = getOrganizationParam();
  return param.organization_id;
}

// =====================
// Query Hooks
// =====================

/**
 * Get all available report templates.
 */
export function useReportTemplates() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report-templates", { orgId }],
    queryFn: async () => {
      const response = await reportsAPI.getTemplates();
      return response.data;
    },
    staleTime: 1000 * 60 * 30, // Templates rarely change, cache for 30 min
  });
}

/**
 * Get a specific report template.
 */
export function useReportTemplate(templateId: string | null) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report-template", templateId, { orgId }],
    queryFn: async () => {
      if (!templateId) throw new Error("Template ID required");
      const response = await reportsAPI.getTemplate(templateId);
      return response.data;
    },
    enabled: !!templateId,
  });
}

/**
 * Get list of reports (report history).
 */
export function useReportHistory(params?: {
  status?: ReportStatus;
  report_type?: ReportType;
  limit?: number;
  offset?: number;
}) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["reports", params, { orgId }],
    queryFn: async () => {
      const response = await reportsAPI.getReports(params);
      return response.data;
    },
  });
}

/**
 * Get details of a specific report.
 */
export function useReportDetail(reportId: string | null) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report", reportId, { orgId }],
    queryFn: async () => {
      if (!reportId) throw new Error("Report ID required");
      const response = await reportsAPI.getReport(reportId);
      return response.data;
    },
    enabled: !!reportId,
  });
}

/**
 * Poll for report generation status.
 * Automatically refetches every 2 seconds while status is 'generating'.
 */
export function useReportStatus(
  reportId: string | null,
  enabled: boolean = true,
) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report-status", reportId, { orgId }],
    queryFn: async () => {
      if (!reportId) throw new Error("Report ID required");
      const response = await reportsAPI.getStatus(reportId);
      return response.data;
    },
    enabled: !!reportId && enabled,
    refetchInterval: (query) => {
      // Poll every 2 seconds while generating
      const status = query.state.data?.status;
      return status === "generating" ? 2000 : false;
    },
  });
}

/**
 * Get list of scheduled reports.
 */
export function useReportSchedules() {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report-schedules", { orgId }],
    queryFn: async () => {
      const response = await reportsAPI.getSchedules();
      return response.data;
    },
  });
}

/**
 * Get details of a specific schedule.
 */
export function useScheduleDetail(scheduleId: string | null) {
  const orgId = getOrgKeyPart();
  return useQuery({
    queryKey: ["report-schedule", scheduleId, { orgId }],
    queryFn: async () => {
      if (!scheduleId) throw new Error("Schedule ID required");
      const response = await reportsAPI.getSchedule(scheduleId);
      return response.data;
    },
    enabled: !!scheduleId,
  });
}

// =====================
// Mutation Hooks
// =====================

/**
 * Generate a new report.
 */
export function useGenerateReport() {
  const queryClient = useQueryClient();
  const orgId = getOrgKeyPart();

  return useMutation({
    mutationFn: async (data: ReportGenerateRequest) => {
      const response = await reportsAPI.generate(data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate report list to show new report
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

/**
 * Delete a report.
 */
export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reportId: string) => {
      await reportsAPI.deleteReport(reportId);
      return reportId;
    },
    onSuccess: (reportId) => {
      // Invalidate report list
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      // Remove specific report from cache
      queryClient.removeQueries({ queryKey: ["report", reportId] });
    },
  });
}

/**
 * Download a report file.
 */
export function useDownloadReport() {
  return useMutation({
    mutationFn: async ({
      reportId,
      format,
      filename,
    }: {
      reportId: string;
      format?: ReportFormat;
      filename?: string;
    }) => {
      const blob = await reportsAPI.download(reportId, format);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || `report-${reportId}.${format || "pdf"}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { reportId, format };
    },
  });
}

/**
 * Share a report with users.
 */
export function useShareReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      reportId,
      data,
    }: {
      reportId: string;
      data: ReportShareRequest;
    }) => {
      const response = await reportsAPI.share(reportId, data);
      return response.data;
    },
    onSuccess: (data, { reportId }) => {
      // Update specific report in cache
      queryClient.setQueryData(["report", reportId], data);
    },
  });
}

/**
 * Create a new scheduled report.
 */
export function useCreateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ReportScheduleRequest) => {
      const response = await reportsAPI.createSchedule(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report-schedules"] });
    },
  });
}

/**
 * Update an existing schedule.
 */
export function useUpdateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      scheduleId,
      data,
    }: {
      scheduleId: string;
      data: Partial<ReportScheduleRequest>;
    }) => {
      const response = await reportsAPI.updateSchedule(scheduleId, data);
      return response.data;
    },
    onSuccess: (data, { scheduleId }) => {
      queryClient.invalidateQueries({ queryKey: ["report-schedules"] });
      queryClient.setQueryData(["report-schedule", scheduleId], data);
    },
  });
}

/**
 * Delete a schedule.
 */
export function useDeleteSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (scheduleId: string) => {
      await reportsAPI.deleteSchedule(scheduleId);
      return scheduleId;
    },
    onSuccess: (scheduleId) => {
      queryClient.invalidateQueries({ queryKey: ["report-schedules"] });
      queryClient.removeQueries({ queryKey: ["report-schedule", scheduleId] });
    },
  });
}

/**
 * Trigger immediate execution of a scheduled report.
 */
export function useRunScheduleNow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (scheduleId: string) => {
      const response = await reportsAPI.runScheduleNow(scheduleId);
      return response.data;
    },
    onSuccess: () => {
      // Refresh reports list to show generating report
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      queryClient.invalidateQueries({ queryKey: ["report-schedules"] });
    },
  });
}

/**
 * Generate a lightweight preview of report data.
 * Returns truncated data for display before full generation.
 */
export function useReportPreview() {
  return useMutation({
    mutationFn: async (
      data: ReportGenerateRequest,
    ): Promise<ReportPreviewData> => {
      const response = await reportsAPI.preview(data);
      return response.data;
    },
  });
}
