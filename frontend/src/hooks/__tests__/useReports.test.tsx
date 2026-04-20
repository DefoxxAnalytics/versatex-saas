/**
 * Tests for useReports hooks
 *
 * Tests cover:
 * - Report template fetching
 * - Report history listing
 * - Report generation
 * - Report status polling
 * - Report downloading
 * - Report scheduling CRUD
 * - Report preview
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useReportTemplates,
  useReportTemplate,
  useReportHistory,
  useReportDetail,
  useReportStatus,
  useReportSchedules,
  useScheduleDetail,
  useGenerateReport,
  useDeleteReport,
  useDownloadReport,
  useShareReport,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useRunScheduleNow,
  useReportPreview,
} from "../useReports";
import * as api from "@/lib/api";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  reportsAPI: {
    getTemplates: vi.fn(),
    getTemplate: vi.fn(),
    getReports: vi.fn(),
    getReport: vi.fn(),
    getStatus: vi.fn(),
    getSchedules: vi.fn(),
    getSchedule: vi.fn(),
    generate: vi.fn(),
    deleteReport: vi.fn(),
    download: vi.fn(),
    share: vi.fn(),
    createSchedule: vi.fn(),
    updateSchedule: vi.fn(),
    deleteSchedule: vi.fn(),
    runScheduleNow: vi.fn(),
    preview: vi.fn(),
  },
  getOrganizationParam: vi.fn(),
}));

// Mock data
const mockTemplates = [
  {
    id: "executive-summary",
    name: "Executive Summary",
    category: "Executive & Overview",
  },
  {
    id: "spend-analysis",
    name: "Spend Analysis",
    category: "Supplier Intelligence",
  },
];

const mockReports = {
  results: [
    {
      id: "1",
      report_type: "executive-summary",
      status: "completed",
      created_at: "2024-01-15",
    },
    {
      id: "2",
      report_type: "spend-analysis",
      status: "generating",
      created_at: "2024-01-16",
    },
  ],
  count: 2,
};

const mockSchedules = {
  results: [
    {
      id: "s1",
      report_type: "executive-summary",
      frequency: "weekly",
      is_active: true,
    },
  ],
  count: 1,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useReports Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getOrganizationParam).mockReturnValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // =====================
  // useReportTemplates Tests
  // =====================
  describe("useReportTemplates", () => {
    it("should fetch report templates", async () => {
      vi.mocked(api.reportsAPI.getTemplates).mockResolvedValue({
        data: mockTemplates,
      } as any);

      const { result } = renderHook(() => useReportTemplates(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getTemplates).toHaveBeenCalled();
      expect(result.current.data).toEqual(mockTemplates);
    });

    it("should handle template fetch error", async () => {
      vi.mocked(api.reportsAPI.getTemplates).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useReportTemplates(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
    });
  });

  // =====================
  // useReportTemplate Tests
  // =====================
  describe("useReportTemplate", () => {
    it("should fetch single template when ID provided", async () => {
      const template = { id: "executive-summary", name: "Executive Summary" };
      vi.mocked(api.reportsAPI.getTemplate).mockResolvedValue({
        data: template,
      } as any);

      const { result } = renderHook(
        () => useReportTemplate("executive-summary"),
        {
          wrapper: createWrapper(),
        },
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getTemplate).toHaveBeenCalledWith(
        "executive-summary",
      );
      expect(result.current.data).toEqual(template);
    });

    it("should not fetch when ID is null", () => {
      const { result } = renderHook(() => useReportTemplate(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(api.reportsAPI.getTemplate).not.toHaveBeenCalled();
    });
  });

  // =====================
  // useReportHistory Tests
  // =====================
  describe("useReportHistory", () => {
    it("should fetch report history", async () => {
      vi.mocked(api.reportsAPI.getReports).mockResolvedValue({
        data: mockReports,
      } as any);

      const { result } = renderHook(() => useReportHistory(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getReports).toHaveBeenCalled();
      expect(result.current.data).toEqual(mockReports);
    });

    it("should pass filter params to API", async () => {
      vi.mocked(api.reportsAPI.getReports).mockResolvedValue({
        data: mockReports,
      } as any);

      const params = { status: "completed" as const, limit: 10 };
      const { result } = renderHook(() => useReportHistory(params), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getReports).toHaveBeenCalledWith(params);
    });
  });

  // =====================
  // useReportDetail Tests
  // =====================
  describe("useReportDetail", () => {
    it("should fetch report details", async () => {
      const report = {
        id: "1",
        report_type: "executive-summary",
        status: "completed",
      };
      vi.mocked(api.reportsAPI.getReport).mockResolvedValue({
        data: report,
      } as any);

      const { result } = renderHook(() => useReportDetail("1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getReport).toHaveBeenCalledWith("1");
    });

    it("should not fetch when ID is null", () => {
      const { result } = renderHook(() => useReportDetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // useReportStatus Tests
  // =====================
  describe("useReportStatus", () => {
    it("should poll status for generating reports", async () => {
      const status = { id: "1", status: "generating", progress: 50 };
      vi.mocked(api.reportsAPI.getStatus).mockResolvedValue({
        data: status,
      } as any);

      const { result } = renderHook(() => useReportStatus("1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getStatus).toHaveBeenCalledWith("1");
    });

    it("should not fetch when disabled", () => {
      const { result } = renderHook(() => useReportStatus("1", false), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });

    it("should not fetch when ID is null", () => {
      const { result } = renderHook(() => useReportStatus(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // useReportSchedules Tests
  // =====================
  describe("useReportSchedules", () => {
    it("should fetch schedules", async () => {
      vi.mocked(api.reportsAPI.getSchedules).mockResolvedValue({
        data: mockSchedules,
      } as any);

      const { result } = renderHook(() => useReportSchedules(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getSchedules).toHaveBeenCalled();
    });
  });

  // =====================
  // useScheduleDetail Tests
  // =====================
  describe("useScheduleDetail", () => {
    it("should fetch schedule details", async () => {
      const schedule = {
        id: "s1",
        report_type: "executive-summary",
        frequency: "weekly",
      };
      vi.mocked(api.reportsAPI.getSchedule).mockResolvedValue({
        data: schedule,
      } as any);

      const { result } = renderHook(() => useScheduleDetail("s1"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.reportsAPI.getSchedule).toHaveBeenCalledWith("s1");
    });

    it("should not fetch when ID is null", () => {
      const { result } = renderHook(() => useScheduleDetail(null), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  // =====================
  // useGenerateReport Tests
  // =====================
  describe("useGenerateReport", () => {
    it("should generate report", async () => {
      const generatedReport = { id: "3", status: "generating" };
      vi.mocked(api.reportsAPI.generate).mockResolvedValue({
        data: generatedReport,
      } as any);

      const { result } = renderHook(() => useGenerateReport(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync({
          report_type: "executive-summary",
          title: "Test Report",
        } as any);
      });

      expect(api.reportsAPI.generate).toHaveBeenCalled();
      expect(returnedData).toEqual(generatedReport);
    });

    it("should handle generation error", async () => {
      vi.mocked(api.reportsAPI.generate).mockRejectedValue(
        new Error("Generation failed"),
      );

      const { result } = renderHook(() => useGenerateReport(), {
        wrapper: createWrapper(),
      });

      let errorOccurred = false;
      await act(async () => {
        try {
          await result.current.mutateAsync({
            report_type: "executive-summary",
            title: "Test Report",
          } as any);
        } catch {
          errorOccurred = true;
        }
      });

      expect(errorOccurred).toBe(true);
    });
  });

  // =====================
  // useDeleteReport Tests
  // =====================
  describe("useDeleteReport", () => {
    it("should delete report", async () => {
      vi.mocked(api.reportsAPI.deleteReport).mockResolvedValue({} as any);

      const { result } = renderHook(() => useDeleteReport(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync("1");
      });

      expect(api.reportsAPI.deleteReport).toHaveBeenCalledWith("1");
    });
  });

  // =====================
  // useDownloadReport Tests
  // =====================
  describe("useDownloadReport", () => {
    it("should download report and trigger browser download", async () => {
      const mockBlob = new Blob(["test content"], { type: "application/pdf" });
      vi.mocked(api.reportsAPI.download).mockResolvedValue(mockBlob);

      // Store original URL functions
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;

      // Mock URL methods
      const mockUrl = "blob:mock-url";
      URL.createObjectURL = vi.fn().mockReturnValue(mockUrl);
      URL.revokeObjectURL = vi.fn();

      // Track link creation using a proxy approach
      let createdLink: HTMLAnchorElement | null = null;
      const originalCreateElement = document.createElement.bind(document);

      // Only mock 'a' element creation
      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string) => {
          const el = originalCreateElement(tagName);
          if (tagName === "a") {
            createdLink = el as HTMLAnchorElement;
            vi.spyOn(createdLink, "click").mockImplementation(() => {});
          }
          return el;
        },
      );

      const { result } = renderHook(() => useDownloadReport(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.mutateAsync({ reportId: "1", format: "pdf" });
      });

      expect(api.reportsAPI.download).toHaveBeenCalledWith("1", "pdf");
      expect(createdLink).not.toBeNull();
      expect(createdLink!.click).toHaveBeenCalled();

      // Restore URL functions
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });
  });

  // =====================
  // useShareReport Tests
  // =====================
  describe("useShareReport", () => {
    it("should share report with users", async () => {
      const sharedReport = { id: "1", shared_with: [1, 2] };
      vi.mocked(api.reportsAPI.share).mockResolvedValue({
        data: sharedReport,
      } as any);

      const { result } = renderHook(() => useShareReport(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync({
          reportId: "1",
          data: { user_ids: [1, 2] } as any,
        });
      });

      expect(api.reportsAPI.share).toHaveBeenCalledWith("1", {
        user_ids: [1, 2],
      });
      expect(returnedData).toEqual(sharedReport);
    });
  });

  // =====================
  // useCreateSchedule Tests
  // =====================
  describe("useCreateSchedule", () => {
    it("should create schedule", async () => {
      const newSchedule = {
        id: "s2",
        report_type: "spend-analysis",
        frequency: "monthly",
      };
      vi.mocked(api.reportsAPI.createSchedule).mockResolvedValue({
        data: newSchedule,
      } as any);

      const { result } = renderHook(() => useCreateSchedule(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync({
          report_type: "spend-analysis",
          frequency: "monthly",
        } as any);
      });

      expect(api.reportsAPI.createSchedule).toHaveBeenCalled();
      expect(returnedData).toEqual(newSchedule);
    });
  });

  // =====================
  // useUpdateSchedule Tests
  // =====================
  describe("useUpdateSchedule", () => {
    it("should update schedule", async () => {
      const updatedSchedule = { id: "s1", frequency: "daily" };
      vi.mocked(api.reportsAPI.updateSchedule).mockResolvedValue({
        data: updatedSchedule,
      } as any);

      const { result } = renderHook(() => useUpdateSchedule(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync({
          scheduleId: "s1",
          data: { frequency: "daily" } as any,
        });
      });

      expect(api.reportsAPI.updateSchedule).toHaveBeenCalledWith("s1", {
        frequency: "daily",
      });
      expect(returnedData).toEqual(updatedSchedule);
    });
  });

  // =====================
  // useDeleteSchedule Tests
  // =====================
  describe("useDeleteSchedule", () => {
    it("should delete schedule", async () => {
      vi.mocked(api.reportsAPI.deleteSchedule).mockResolvedValue({} as any);

      const { result } = renderHook(() => useDeleteSchedule(), {
        wrapper: createWrapper(),
      });

      let didResolve = false;
      await act(async () => {
        await result.current.mutateAsync("s1");
        didResolve = true;
      });

      expect(api.reportsAPI.deleteSchedule).toHaveBeenCalledWith("s1");
      expect(didResolve).toBe(true);
    });
  });

  // =====================
  // useRunScheduleNow Tests
  // =====================
  describe("useRunScheduleNow", () => {
    it("should trigger immediate schedule run", async () => {
      const runResult = { report_id: "4", status: "generating" };
      vi.mocked(api.reportsAPI.runScheduleNow).mockResolvedValue({
        data: runResult,
      } as any);

      const { result } = renderHook(() => useRunScheduleNow(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync("s1");
      });

      expect(api.reportsAPI.runScheduleNow).toHaveBeenCalledWith("s1");
      expect(returnedData).toEqual(runResult);
    });
  });

  // =====================
  // useReportPreview Tests
  // =====================
  describe("useReportPreview", () => {
    it("should generate preview data", async () => {
      const previewData = {
        metrics: { total_spend: 100000 },
        top_categories: [{ name: "IT", spend: 50000 }],
      };
      vi.mocked(api.reportsAPI.preview).mockResolvedValue({
        data: previewData,
      } as any);

      const { result } = renderHook(() => useReportPreview(), {
        wrapper: createWrapper(),
      });

      let returnedData: any;
      await act(async () => {
        returnedData = await result.current.mutateAsync({
          report_type: "executive-summary",
          title: "Preview Test",
        } as any);
      });

      expect(api.reportsAPI.preview).toHaveBeenCalled();
      expect(returnedData).toEqual(previewData);
    });

    it("should handle preview error", async () => {
      vi.mocked(api.reportsAPI.preview).mockRejectedValue(
        new Error("Preview failed"),
      );

      const { result } = renderHook(() => useReportPreview(), {
        wrapper: createWrapper(),
      });

      let errorOccurred = false;
      await act(async () => {
        try {
          await result.current.mutateAsync({
            report_type: "executive-summary",
            title: "Preview Test",
          } as any);
        } catch {
          errorOccurred = true;
        }
      });

      expect(errorOccurred).toBe(true);
    });
  });
});
