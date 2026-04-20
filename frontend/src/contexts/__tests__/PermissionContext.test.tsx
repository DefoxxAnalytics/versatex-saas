/**
 * Tests for PermissionContext
 *
 * Tests cover:
 * - Permission checking (hasPermission)
 * - Multiple permission checks (hasAllPermissions, hasAnyPermission)
 * - Role hierarchy (isAtLeast)
 * - Role-based boolean flags (isAdmin, isManagerOrAbove)
 * - Super admin detection
 * - Denial messages
 * - Edge cases (no role, null user)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  PermissionProvider,
  usePermissions,
  useHasPermission,
  useIsAdmin,
} from "../PermissionContext";
import { AuthProvider } from "../AuthContext";
import * as authLib from "@/lib/auth";

// Mock dependencies
vi.mock("@/lib/auth", () => ({
  isAuthenticated: vi.fn(),
  clearSession: vi.fn(),
  updateActivity: vi.fn(),
  getRemainingSessionTime: vi.fn(),
  getUserData: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  authAPI: {
    logout: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Test consumer for full context
function TestConsumer() {
  const ctx = usePermissions();
  return (
    <div>
      <span data-testid="role">{ctx.role ?? "null"}</span>
      <span data-testid="isAdmin">{String(ctx.isAdmin)}</span>
      <span data-testid="isManagerOrAbove">{String(ctx.isManagerOrAbove)}</span>
      <span data-testid="isSuperAdmin">{String(ctx.isSuperAdmin)}</span>
      <span data-testid="canUploadForAnyOrg">
        {String(ctx.canUploadForAnyOrg)}
      </span>
      <span data-testid="hasView">{String(ctx.hasPermission("view"))}</span>
      <span data-testid="hasUpload">{String(ctx.hasPermission("upload"))}</span>
      <span data-testid="hasExport">{String(ctx.hasPermission("export"))}</span>
      <span data-testid="hasDelete">{String(ctx.hasPermission("delete"))}</span>
      <span data-testid="hasClear">{String(ctx.hasPermission("clear"))}</span>
      <span data-testid="hasAdminPanel">
        {String(ctx.hasPermission("admin_panel"))}
      </span>
      <span data-testid="hasAllViewUpload">
        {String(ctx.hasAllPermissions(["view", "upload"]))}
      </span>
      <span data-testid="hasAnyDeleteClear">
        {String(ctx.hasAnyPermission(["delete", "clear"]))}
      </span>
      <span data-testid="isAtLeastViewer">
        {String(ctx.isAtLeast("viewer"))}
      </span>
      <span data-testid="isAtLeastManager">
        {String(ctx.isAtLeast("manager"))}
      </span>
      <span data-testid="isAtLeastAdmin">{String(ctx.isAtLeast("admin"))}</span>
      <span data-testid="denialView">{ctx.getDenialMessage("view")}</span>
      <span data-testid="denialDelete">{ctx.getDenialMessage("delete")}</span>
    </div>
  );
}

// Test consumer for useHasPermission hook
function HasPermissionConsumer({
  permission,
}: {
  permission: "view" | "upload" | "export" | "delete" | "clear" | "admin_panel";
}) {
  const hasIt = useHasPermission(permission);
  return <span data-testid="result">{String(hasIt)}</span>;
}

// Test consumer for useIsAdmin hook
function IsAdminConsumer() {
  const isAdmin = useIsAdmin();
  return <span data-testid="result">{String(isAdmin)}</span>;
}

function createWrapper() {
  return ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>
      <PermissionProvider>{children}</PermissionProvider>
    </AuthProvider>
  );
}

// Mock users
const adminUser = {
  id: 1,
  username: "admin",
  email: "admin@test.com",
  profile: {
    organization: 1,
    role: "admin" as const,
    is_super_admin: false,
  },
};

const managerUser = {
  id: 2,
  username: "manager",
  email: "manager@test.com",
  profile: {
    organization: 1,
    role: "manager" as const,
    is_super_admin: false,
  },
};

const viewerUser = {
  id: 3,
  username: "viewer",
  email: "viewer@test.com",
  profile: {
    organization: 1,
    role: "viewer" as const,
    is_super_admin: false,
  },
};

const superAdminUser = {
  id: 4,
  username: "superadmin",
  email: "super@test.com",
  profile: {
    organization: 1,
    role: "admin" as const,
    is_super_admin: true,
  },
};

describe("PermissionContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authLib.getRemainingSessionTime).mockReturnValue(30 * 60 * 1000);
  });

  // =====================
  // Unauthenticated State
  // =====================
  describe("Unauthenticated State", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);
      vi.mocked(authLib.getUserData).mockReturnValue(null);
    });

    it("should have role=null when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("role")).toHaveTextContent("null");
    });

    it("should deny all permissions when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasView")).toHaveTextContent("false");
      expect(screen.getByTestId("hasUpload")).toHaveTextContent("false");
      expect(screen.getByTestId("hasExport")).toHaveTextContent("false");
      expect(screen.getByTestId("hasDelete")).toHaveTextContent("false");
      expect(screen.getByTestId("hasClear")).toHaveTextContent("false");
      expect(screen.getByTestId("hasAdminPanel")).toHaveTextContent("false");
    });

    it("should have isAdmin=false when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAdmin")).toHaveTextContent("false");
    });

    it("should have isManagerOrAbove=false when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isManagerOrAbove")).toHaveTextContent("false");
    });

    it("should return false for isAtLeast when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAtLeastViewer")).toHaveTextContent("false");
      expect(screen.getByTestId("isAtLeastManager")).toHaveTextContent("false");
      expect(screen.getByTestId("isAtLeastAdmin")).toHaveTextContent("false");
    });
  });

  // =====================
  // Admin Role Tests
  // =====================
  describe("Admin Role", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(adminUser);
    });

    it("should have role=admin", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("role")).toHaveTextContent("admin");
    });

    it("should have all permissions", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasView")).toHaveTextContent("true");
      expect(screen.getByTestId("hasUpload")).toHaveTextContent("true");
      expect(screen.getByTestId("hasExport")).toHaveTextContent("true");
      expect(screen.getByTestId("hasDelete")).toHaveTextContent("true");
      expect(screen.getByTestId("hasClear")).toHaveTextContent("true");
      expect(screen.getByTestId("hasAdminPanel")).toHaveTextContent("true");
    });

    it("should have isAdmin=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAdmin")).toHaveTextContent("true");
    });

    it("should have isManagerOrAbove=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isManagerOrAbove")).toHaveTextContent("true");
    });

    it("should pass isAtLeast for all roles", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAtLeastViewer")).toHaveTextContent("true");
      expect(screen.getByTestId("isAtLeastManager")).toHaveTextContent("true");
      expect(screen.getByTestId("isAtLeastAdmin")).toHaveTextContent("true");
    });

    it("should return true for hasAllPermissions with admin permissions", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasAllViewUpload")).toHaveTextContent("true");
    });

    it("should return true for hasAnyPermission with delete or clear", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasAnyDeleteClear")).toHaveTextContent("true");
    });
  });

  // =====================
  // Manager Role Tests
  // =====================
  describe("Manager Role", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(managerUser);
    });

    it("should have role=manager", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("role")).toHaveTextContent("manager");
    });

    it("should have view, upload, export permissions", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasView")).toHaveTextContent("true");
      expect(screen.getByTestId("hasUpload")).toHaveTextContent("true");
      expect(screen.getByTestId("hasExport")).toHaveTextContent("true");
    });

    it("should NOT have delete, clear, admin_panel permissions", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasDelete")).toHaveTextContent("false");
      expect(screen.getByTestId("hasClear")).toHaveTextContent("false");
      expect(screen.getByTestId("hasAdminPanel")).toHaveTextContent("false");
    });

    it("should have isAdmin=false", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAdmin")).toHaveTextContent("false");
    });

    it("should have isManagerOrAbove=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isManagerOrAbove")).toHaveTextContent("true");
    });

    it("should pass isAtLeast for viewer and manager", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAtLeastViewer")).toHaveTextContent("true");
      expect(screen.getByTestId("isAtLeastManager")).toHaveTextContent("true");
      expect(screen.getByTestId("isAtLeastAdmin")).toHaveTextContent("false");
    });

    it("should return true for hasAllPermissions with view+upload", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasAllViewUpload")).toHaveTextContent("true");
    });

    it("should return false for hasAnyPermission with delete or clear", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasAnyDeleteClear")).toHaveTextContent(
        "false",
      );
    });
  });

  // =====================
  // Viewer Role Tests
  // =====================
  describe("Viewer Role", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(viewerUser);
    });

    it("should have role=viewer", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("role")).toHaveTextContent("viewer");
    });

    it("should have only view permission", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasView")).toHaveTextContent("true");
    });

    it("should NOT have upload, export, delete, clear, admin_panel", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasUpload")).toHaveTextContent("false");
      expect(screen.getByTestId("hasExport")).toHaveTextContent("false");
      expect(screen.getByTestId("hasDelete")).toHaveTextContent("false");
      expect(screen.getByTestId("hasClear")).toHaveTextContent("false");
      expect(screen.getByTestId("hasAdminPanel")).toHaveTextContent("false");
    });

    it("should have isAdmin=false", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAdmin")).toHaveTextContent("false");
    });

    it("should have isManagerOrAbove=false", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isManagerOrAbove")).toHaveTextContent("false");
    });

    it("should only pass isAtLeast for viewer", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isAtLeastViewer")).toHaveTextContent("true");
      expect(screen.getByTestId("isAtLeastManager")).toHaveTextContent("false");
      expect(screen.getByTestId("isAtLeastAdmin")).toHaveTextContent("false");
    });

    it("should return false for hasAllPermissions with view+upload", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("hasAllViewUpload")).toHaveTextContent("false");
    });
  });

  // =====================
  // Super Admin Tests
  // =====================
  describe("Super Admin", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(superAdminUser);
    });

    it("should have isSuperAdmin=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("true");
    });

    it("should have canUploadForAnyOrg=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("canUploadForAnyOrg")).toHaveTextContent(
        "true",
      );
    });
  });

  // =====================
  // Non-Super Admin Tests
  // =====================
  describe("Non-Super Admin", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(adminUser);
    });

    it("should have isSuperAdmin=false", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("false");
    });

    it("should have canUploadForAnyOrg=false", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("canUploadForAnyOrg")).toHaveTextContent(
        "false",
      );
    });
  });

  // =====================
  // Denial Messages Tests
  // =====================
  describe("Denial Messages", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(viewerUser);
    });

    it("should return correct denial message for view", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("denialView")).toHaveTextContent(
        "You do not have permission to view this content",
      );
    });

    it("should return correct denial message for delete", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("denialDelete")).toHaveTextContent(
        "Only Admins can delete transactions",
      );
    });
  });

  // =====================
  // useHasPermission Hook Tests
  // =====================
  describe("useHasPermission Hook", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(managerUser);
    });

    it("should return true for allowed permission", async () => {
      render(<HasPermissionConsumer permission="view" />, {
        wrapper: createWrapper(),
      });
      expect(screen.getByTestId("result")).toHaveTextContent("true");
    });

    it("should return false for disallowed permission", async () => {
      render(<HasPermissionConsumer permission="delete" />, {
        wrapper: createWrapper(),
      });
      expect(screen.getByTestId("result")).toHaveTextContent("false");
    });
  });

  // =====================
  // useIsAdmin Hook Tests
  // =====================
  describe("useIsAdmin Hook", () => {
    it("should return true for admin", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(adminUser);

      render(<IsAdminConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("result")).toHaveTextContent("true");
    });

    it("should return false for non-admin", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(viewerUser);

      render(<IsAdminConsumer />, { wrapper: createWrapper() });
      expect(screen.getByTestId("result")).toHaveTextContent("false");
    });
  });

  // =====================
  // usePermissions Hook Error
  // =====================
  describe("usePermissions Hook Error", () => {
    it("should throw error when used outside provider", () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const BadConsumer = () => {
        const ctx = usePermissions();
        return <div>{ctx.role}</div>;
      };

      expect(() => {
        render(<BadConsumer />);
      }).toThrow("usePermissions must be used within a PermissionProvider");

      consoleSpy.mockRestore();
    });
  });
});
