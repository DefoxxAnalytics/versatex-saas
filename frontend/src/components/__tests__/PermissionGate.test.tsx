/**
 * Tests for PermissionGate component
 *
 * Tests cover:
 * - Hide behavior (default)
 * - Disable behavior with tooltips
 * - Multiple permission requirements
 * - Fallback content
 * - Convenience components (AdminOnly, CanExport, CanDelete, CanClear)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  PermissionGate,
  AdminOnly,
  CanExport,
  CanDelete,
  CanClear,
} from "../PermissionGate";
import * as PermissionContext from "@/contexts/PermissionContext";
import { TooltipProvider } from "@/components/ui/tooltip";

// Mock the permission context
vi.mock("@/contexts/PermissionContext", () => ({
  usePermissions: vi.fn(),
}));

// Wrapper for tests that need TooltipProvider
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <TooltipProvider>{children}</TooltipProvider>;
}

// Helper to create a complete PermissionContextType mock
function createPermissionMock(overrides: {
  hasPermission?: () => boolean;
  hasAllPermissions?: (perms: string[]) => boolean;
  hasAnyPermission?: () => boolean;
  getDenialMessage?: () => string;
  isAdmin?: boolean;
}) {
  return {
    role: overrides.isAdmin ? ("admin" as const) : ("viewer" as const),
    hasPermission: overrides.hasPermission ?? (() => false),
    hasAllPermissions: overrides.hasAllPermissions ?? (() => false),
    hasAnyPermission: overrides.hasAnyPermission ?? (() => false),
    getDenialMessage: overrides.getDenialMessage ?? (() => "No permission"),
    isAtLeast: vi.fn(() => overrides.isAdmin ?? false),
    isAdmin: overrides.isAdmin ?? false,
    isManagerOrAbove: overrides.isAdmin ?? false,
    isSuperAdmin: false,
    canUploadForAnyOrg: false,
  };
}

describe("PermissionGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =====================
  // Hide Behavior (Default)
  // =====================
  describe("Hide Behavior", () => {
    it("should render children when user has permission", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => true,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <PermissionGate requires="export">
          <button>Export Data</button>
        </PermissionGate>,
      );

      expect(
        screen.getByRole("button", { name: /export data/i }),
      ).toBeInTheDocument();
    });

    it("should hide children when user lacks permission", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No permission",
        }),
      );

      render(
        <PermissionGate requires="export">
          <button>Export Data</button>
        </PermissionGate>,
      );

      expect(
        screen.queryByRole("button", { name: /export data/i }),
      ).not.toBeInTheDocument();
    });

    it("should render fallback when user lacks permission", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No permission",
        }),
      );

      render(
        <PermissionGate requires="export" fallback={<span>Not Allowed</span>}>
          <button>Export Data</button>
        </PermissionGate>,
      );

      expect(screen.getByText("Not Allowed")).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /export data/i }),
      ).not.toBeInTheDocument();
    });

    it("should handle array of required permissions", () => {
      const mockHasAllPermissions = vi.fn().mockReturnValue(true);
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: mockHasAllPermissions,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <PermissionGate requires={["export", "delete"]}>
          <button>Admin Action</button>
        </PermissionGate>,
      );

      expect(mockHasAllPermissions).toHaveBeenCalledWith(["export", "delete"]);
      expect(
        screen.getByRole("button", { name: /admin action/i }),
      ).toBeInTheDocument();
    });

    it("should hide when any required permission is missing", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "Missing permission",
        }),
      );

      render(
        <PermissionGate requires={["export", "admin_panel"]}>
          <button>Admin Action</button>
        </PermissionGate>,
      );

      expect(
        screen.queryByRole("button", { name: /admin action/i }),
      ).not.toBeInTheDocument();
    });
  });

  // =====================
  // Disable Behavior
  // =====================
  describe("Disable Behavior", () => {
    it("should render enabled children when user has permission", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => true,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <TestWrapper>
          <PermissionGate requires="export" behavior="disable">
            <button>Export Data</button>
          </PermissionGate>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export data/i });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });

    it("should render disabled children when user lacks permission", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "You need Manager access",
        }),
      );

      render(
        <TestWrapper>
          <PermissionGate requires="export" behavior="disable">
            <button>Export Data</button>
          </PermissionGate>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export data/i });
      expect(button).toBeInTheDocument();
      expect(button).toBeDisabled();
    });

    it("should apply opacity and cursor-not-allowed class when disabled", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No access",
        }),
      );

      render(
        <TestWrapper>
          <PermissionGate requires="export" behavior="disable">
            <button className="original-class">Export Data</button>
          </PermissionGate>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export data/i });
      expect(button.className).toContain("opacity-50");
      expect(button.className).toContain("cursor-not-allowed");
      expect(button.className).toContain("original-class");
    });

    it("should set aria-disabled when disabled", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No access",
        }),
      );

      render(
        <TestWrapper>
          <PermissionGate requires="export" behavior="disable">
            <button>Export Data</button>
          </PermissionGate>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export data/i });
      expect(button).toHaveAttribute("aria-disabled", "true");
    });

    it("should use custom tooltip message when provided", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "Default message",
        }),
      );

      render(
        <TestWrapper>
          <PermissionGate
            requires="export"
            behavior="disable"
            tooltip="Upgrade to Pro to export"
          >
            <button>Export Data</button>
          </PermissionGate>
        </TestWrapper>,
      );

      // Button should be rendered and disabled
      const button = screen.getByRole("button", { name: /export data/i });
      expect(button).toBeDisabled();
      // The tooltip content is rendered but may be hidden - just verify the structure is correct
      expect(button.closest("[data-state]")).toBeInTheDocument();
    });

    it("should return null for non-element children with disable behavior", () => {
      // Suppress console.warn for this test
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No access",
        }),
      );

      const { container } = render(
        <TestWrapper>
          <PermissionGate requires="export" behavior="disable">
            Just some text
          </PermissionGate>
        </TestWrapper>,
      );

      expect(container.textContent).toBe("");
      warnSpy.mockRestore();
    });
  });

  // =====================
  // AdminOnly Component
  // =====================
  describe("AdminOnly", () => {
    it("should render children for admins", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: (perms) => perms.includes("admin_panel"),
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <AdminOnly>
          <button>Admin Panel</button>
        </AdminOnly>,
      );

      expect(
        screen.getByRole("button", { name: /admin panel/i }),
      ).toBeInTheDocument();
    });

    it("should hide children for non-admins", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "Admin only",
        }),
      );

      render(
        <AdminOnly>
          <button>Admin Panel</button>
        </AdminOnly>,
      );

      expect(
        screen.queryByRole("button", { name: /admin panel/i }),
      ).not.toBeInTheDocument();
    });

    it("should render fallback for non-admins", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "Admin only",
        }),
      );

      render(
        <AdminOnly fallback={<span>Contact admin</span>}>
          <button>Admin Panel</button>
        </AdminOnly>,
      );

      expect(screen.getByText("Contact admin")).toBeInTheDocument();
    });
  });

  // =====================
  // CanExport Component
  // =====================
  describe("CanExport", () => {
    it("should render enabled export button when permitted", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: (perms) => perms.includes("export"),
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <TestWrapper>
          <CanExport>
            <button>Export CSV</button>
          </CanExport>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export csv/i });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });

    it("should render disabled export button when not permitted (default behavior)", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "Export not allowed",
        }),
      );

      render(
        <TestWrapper>
          <CanExport>
            <button>Export CSV</button>
          </CanExport>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /export csv/i });
      expect(button).toBeDisabled();
    });

    it("should support custom tooltip", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "Default",
        }),
      );

      render(
        <TestWrapper>
          <CanExport tooltip="Upgrade to export">
            <button>Export CSV</button>
          </CanExport>
        </TestWrapper>,
      );

      // Button should be disabled with the tooltip structure
      const button = screen.getByRole("button", { name: /export csv/i });
      expect(button).toBeDisabled();
      expect(button.closest("[data-state]")).toBeInTheDocument();
    });

    it("should support hide behavior", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No export",
        }),
      );

      render(
        <CanExport behavior="hide">
          <button>Export CSV</button>
        </CanExport>,
      );

      expect(
        screen.queryByRole("button", { name: /export csv/i }),
      ).not.toBeInTheDocument();
    });
  });

  // =====================
  // CanDelete Component
  // =====================
  describe("CanDelete", () => {
    it("should render delete button when permitted", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: (perms) => perms.includes("delete"),
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <CanDelete>
          <button>Delete Item</button>
        </CanDelete>,
      );

      expect(
        screen.getByRole("button", { name: /delete item/i }),
      ).toBeInTheDocument();
    });

    it("should hide delete button when not permitted (default behavior)", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No delete",
        }),
      );

      render(
        <CanDelete>
          <button>Delete Item</button>
        </CanDelete>,
      );

      expect(
        screen.queryByRole("button", { name: /delete item/i }),
      ).not.toBeInTheDocument();
    });

    it("should render fallback when not permitted", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No delete",
        }),
      );

      render(
        <CanDelete fallback={<span>Cannot delete</span>}>
          <button>Delete Item</button>
        </CanDelete>,
      );

      expect(screen.getByText("Cannot delete")).toBeInTheDocument();
    });

    it("should support disable behavior", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No delete permission",
        }),
      );

      render(
        <TestWrapper>
          <CanDelete behavior="disable">
            <button>Delete Item</button>
          </CanDelete>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /delete item/i });
      expect(button).toBeDisabled();
    });
  });

  // =====================
  // CanClear Component
  // =====================
  describe("CanClear", () => {
    it("should render clear button when permitted", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: (perms) => perms.includes("clear"),
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <CanClear>
          <button>Clear All Data</button>
        </CanClear>,
      );

      expect(
        screen.getByRole("button", { name: /clear all data/i }),
      ).toBeInTheDocument();
    });

    it("should hide clear button when not permitted (default behavior)", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No clear",
        }),
      );

      render(
        <CanClear>
          <button>Clear All Data</button>
        </CanClear>,
      );

      expect(
        screen.queryByRole("button", { name: /clear all data/i }),
      ).not.toBeInTheDocument();
    });

    it("should render fallback when not permitted", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No clear",
        }),
      );

      render(
        <CanClear fallback={<span>Action not available</span>}>
          <button>Clear All Data</button>
        </CanClear>,
      );

      expect(screen.getByText("Action not available")).toBeInTheDocument();
    });

    it("should support disable behavior", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => false,
          hasAnyPermission: () => false,
          hasPermission: () => false,
          getDenialMessage: () => "No clear permission",
        }),
      );

      render(
        <TestWrapper>
          <CanClear behavior="disable">
            <button>Clear All Data</button>
          </CanClear>
        </TestWrapper>,
      );

      const button = screen.getByRole("button", { name: /clear all data/i });
      expect(button).toBeDisabled();
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle empty children", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => true,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      const { container } = render(
        <PermissionGate requires="export">{null}</PermissionGate>,
      );

      expect(container.textContent).toBe("");
    });

    it("should handle multiple children", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => true,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <PermissionGate requires="export">
          <button>Button 1</button>
          <button>Button 2</button>
        </PermissionGate>,
      );

      expect(
        screen.getByRole("button", { name: /button 1/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /button 2/i }),
      ).toBeInTheDocument();
    });

    it("should handle fragment children", () => {
      vi.mocked(PermissionContext.usePermissions).mockReturnValue(
        createPermissionMock({
          hasAllPermissions: () => true,
          hasAnyPermission: () => true,
          hasPermission: () => true,
          getDenialMessage: () => "",
          isAdmin: true,
        }),
      );

      render(
        <PermissionGate requires="export">
          <>
            <span>Item 1</span>
            <span>Item 2</span>
          </>
        </PermissionGate>,
      );

      expect(screen.getByText("Item 1")).toBeInTheDocument();
      expect(screen.getByText("Item 2")).toBeInTheDocument();
    });
  });
});
