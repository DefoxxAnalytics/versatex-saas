/**
 * Tests for OrganizationContext
 *
 * Tests cover:
 * - Initial state
 * - Single-org users
 * - Multi-org users
 * - Superuser organization access
 * - Organization switching
 * - Role derivation per organization
 * - localStorage persistence
 * - Logout cleanup
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  OrganizationProvider,
  useOrganization,
  getOrganizationParam,
} from "../OrganizationContext";
import { AuthProvider } from "../AuthContext";
import * as authLib from "@/lib/auth";
import * as api from "@/lib/api";

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
  api: {
    get: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Test consumer component
function TestConsumer() {
  const ctx = useOrganization();
  return (
    <div>
      <span data-testid="activeOrg">
        {ctx.activeOrganization?.name ?? "null"}
      </span>
      <span data-testid="activeOrgId">
        {ctx.activeOrganization?.id ?? "null"}
      </span>
      <span data-testid="userOrg">{ctx.userOrganization?.name ?? "null"}</span>
      <span data-testid="orgsCount">{ctx.organizations.length}</span>
      <span data-testid="activeRole">{ctx.activeRole ?? "null"}</span>
      <span data-testid="canSwitch">{String(ctx.canSwitch)}</span>
      <span data-testid="isMultiOrgUser">{String(ctx.isMultiOrgUser)}</span>
      <span data-testid="isViewingOtherOrg">
        {String(ctx.isViewingOtherOrg)}
      </span>
      <span data-testid="isLoading">{String(ctx.isLoading)}</span>
      <button data-testid="switch-2" onClick={() => ctx.switchOrganization(2)}>
        Switch to Org 2
      </button>
      <button data-testid="reset" onClick={() => ctx.resetToDefault()}>
        Reset
      </button>
      <button
        data-testid="getRole-1"
        onClick={() => {
          document.getElementById("roleResult")!.textContent =
            ctx.getRoleInOrg(1) ?? "null";
        }}
      >
        Get Role 1
      </button>
      <span id="roleResult" data-testid="roleResult"></span>
    </div>
  );
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <OrganizationProvider>{children}</OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

// Mock user data
const singleOrgUser = {
  id: 1,
  username: "singleuser",
  email: "single@test.com",
  profile: {
    organization: 1,
    organization_name: "Org One",
    role: "viewer" as const,
    is_super_admin: false,
    organizations: [
      {
        organization: 1,
        organization_name: "Org One",
        organization_slug: "org-one",
        role: "viewer" as const,
        is_primary: true,
      },
    ],
  },
};

const multiOrgUser = {
  id: 2,
  username: "multiuser",
  email: "multi@test.com",
  profile: {
    organization: 1,
    organization_name: "Org One",
    role: "admin" as const,
    is_super_admin: false,
    organizations: [
      {
        organization: 1,
        organization_name: "Org One",
        organization_slug: "org-one",
        role: "admin" as const,
        is_primary: true,
      },
      {
        organization: 2,
        organization_name: "Org Two",
        organization_slug: "org-two",
        role: "viewer" as const,
        is_primary: false,
      },
      {
        organization: 3,
        organization_name: "Org Three",
        organization_slug: "org-three",
        role: "manager" as const,
        is_primary: false,
      },
    ],
  },
};

const superAdminUser = {
  id: 3,
  username: "superadmin",
  email: "super@test.com",
  profile: {
    organization: 1,
    organization_name: "Org One",
    role: "admin" as const,
    is_super_admin: true,
    organizations: [
      {
        organization: 1,
        organization_name: "Org One",
        organization_slug: "org-one",
        role: "admin" as const,
        is_primary: true,
      },
    ],
  },
};

describe("OrganizationContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(authLib.getRemainingSessionTime).mockReturnValue(30 * 60 * 1000);
  });

  afterEach(() => {
    localStorage.clear();
  });

  // =====================
  // Unauthenticated State
  // =====================
  describe("Unauthenticated State", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);
      vi.mocked(authLib.getUserData).mockReturnValue(null);
    });

    it("should have null activeOrganization when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("null");
      });
    });

    it("should have null userOrganization when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("userOrg")).toHaveTextContent("null");
      });
    });

    it("should have empty organizations array when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("orgsCount")).toHaveTextContent("0");
      });
    });

    it("should have canSwitch=false when not authenticated", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("canSwitch")).toHaveTextContent("false");
      });
    });
  });

  // =====================
  // Single-Org User Tests
  // =====================
  describe("Single-Org User", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(singleOrgUser);
    });

    it("should set activeOrganization to primary org", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });
    });

    it("should set userOrganization to primary org", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("userOrg")).toHaveTextContent("Org One");
      });
    });

    it("should have organizations array with single org", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("orgsCount")).toHaveTextContent("1");
      });
    });

    it("should have canSwitch=false for single-org user", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("canSwitch")).toHaveTextContent("false");
      });
    });

    it("should have isMultiOrgUser=false for single-org user", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isMultiOrgUser")).toHaveTextContent("false");
      });
    });

    it("should set activeRole from membership", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeRole")).toHaveTextContent("viewer");
      });
    });

    it("should have isViewingOtherOrg=false when viewing primary", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isViewingOtherOrg")).toHaveTextContent(
          "false",
        );
      });
    });
  });

  // =====================
  // Multi-Org User Tests
  // =====================
  describe("Multi-Org User", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(multiOrgUser);
    });

    it("should have isMultiOrgUser=true", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isMultiOrgUser")).toHaveTextContent("true");
      });
    });

    it("should have canSwitch=true with multiple orgs", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("canSwitch")).toHaveTextContent("true");
      });
    });

    it("should have all orgs in organizations array", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("orgsCount")).toHaveTextContent("3");
      });
    });

    it("should default to primary organization", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });
    });

    it("should use role from primary membership", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeRole")).toHaveTextContent("admin");
      });
    });
  });

  // =====================
  // Organization Switching
  // =====================
  describe("Organization Switching", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(multiOrgUser);
    });

    it("should switch organization when switchOrganization is called", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org Two");
      });
    });

    it("should update activeRole when switching organizations", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeRole")).toHaveTextContent("admin");
      });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("activeRole")).toHaveTextContent("viewer");
      });
    });

    it("should set isViewingOtherOrg=true when viewing non-primary org", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isViewingOtherOrg")).toHaveTextContent(
          "false",
        );
      });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("isViewingOtherOrg")).toHaveTextContent(
          "true",
        );
      });
    });

    it("should persist selection to localStorage", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      expect(localStorage.getItem("active_organization_id")).toBe("2");
    });

    it("should reset to default when resetToDefault is called", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org Two");
      });

      await act(async () => {
        screen.getByTestId("reset").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
        expect(screen.getByTestId("isViewingOtherOrg")).toHaveTextContent(
          "false",
        );
      });
    });

    it("should clear localStorage when resetToDefault is called", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await act(async () => {
        screen.getByTestId("switch-2").click();
      });

      expect(localStorage.getItem("active_organization_id")).toBe("2");

      await act(async () => {
        screen.getByTestId("reset").click();
      });

      expect(localStorage.getItem("active_organization_id")).toBeNull();
    });
  });

  // =====================
  // Superuser Tests
  // =====================
  describe("Superuser", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(superAdminUser);
      vi.mocked(api.api.get).mockResolvedValue({
        data: [
          { id: 1, name: "Org One", slug: "org-one", is_active: true },
          { id: 2, name: "Org Two", slug: "org-two", is_active: true },
          { id: 3, name: "Org Three", slug: "org-three", is_active: true },
        ],
      });
    });

    it("should fetch all organizations for superuser", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(api.api.get).toHaveBeenCalledWith("/auth/organizations/");
      });
    });

    it("should have canSwitch=true for superuser with multiple orgs", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("canSwitch")).toHaveTextContent("true");
      });
    });

    it("should always return admin role for superuser via getRoleInOrg", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
      });

      await act(async () => {
        screen.getByTestId("getRole-1").click();
      });

      expect(screen.getByTestId("roleResult")).toHaveTextContent("admin");
    });
  });

  // =====================
  // getRoleInOrg Tests
  // =====================
  describe("getRoleInOrg", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(multiOrgUser);
    });

    it("should return correct role for org in membership", async () => {
      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
      });

      await act(async () => {
        screen.getByTestId("getRole-1").click();
      });

      expect(screen.getByTestId("roleResult")).toHaveTextContent("admin");
    });
  });

  // =====================
  // localStorage Persistence
  // =====================
  describe("localStorage Persistence", () => {
    beforeEach(() => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(multiOrgUser);
    });

    it("should restore persisted org on mount", async () => {
      localStorage.setItem("active_organization_id", "2");

      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org Two");
      });
    });

    it("should use primary org if persisted org not found", async () => {
      localStorage.setItem("active_organization_id", "999");

      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });
    });

    it("should clear invalid persisted org from localStorage", async () => {
      localStorage.setItem("active_organization_id", "999");

      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
      });

      expect(localStorage.getItem("active_organization_id")).toBeNull();
    });
  });

  // =====================
  // useOrganization Hook Tests
  // =====================
  describe("useOrganization Hook", () => {
    it("should throw error when used outside provider", () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const BadConsumer = () => {
        const ctx = useOrganization();
        return <div>{ctx.activeOrganization?.name}</div>;
      };

      expect(() => {
        render(<BadConsumer />);
      }).toThrow("useOrganization must be used within an OrganizationProvider");

      consoleSpy.mockRestore();
    });
  });

  // =====================
  // getOrganizationParam Tests
  // =====================
  describe("getOrganizationParam", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("should return empty object when no org stored", () => {
      const result = getOrganizationParam();
      expect(result).toEqual({});
    });

    it("should return organization_id when stored", () => {
      localStorage.setItem("active_organization_id", "5");
      const result = getOrganizationParam();
      expect(result).toEqual({ organization_id: 5 });
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle user without profile.organizations", async () => {
      const userNoOrgs = {
        id: 1,
        username: "test",
        email: "test@test.com",
        profile: {
          organization: 1,
          organization_name: "Org One",
          role: "viewer" as const,
          is_super_admin: false,
        },
      };

      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(userNoOrgs as any);

      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
        expect(screen.getByTestId("isMultiOrgUser")).toHaveTextContent("false");
      });
    });

    it("should handle superuser API failure gracefully", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(superAdminUser);
      vi.mocked(api.api.get).mockRejectedValue(new Error("Network error"));

      render(<TestConsumer />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
        // Should fall back to user's primary org
        expect(screen.getByTestId("activeOrg")).toHaveTextContent("Org One");
      });
    });
  });
});
