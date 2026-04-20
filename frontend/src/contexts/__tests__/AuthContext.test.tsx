/**
 * Tests for AuthContext
 *
 * Tests cover:
 * - Initial state and loading
 * - Authentication checking
 * - User role derivation
 * - Login/logout flows
 * - Super admin detection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../AuthContext";
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
}));

vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

// Test component to access context
function TestConsumer() {
  const { isAuth, user, role, isSuperAdmin, logout, checkAuth, refreshUser } =
    useAuth();
  return (
    <div>
      <span data-testid="isAuth">{String(isAuth)}</span>
      <span data-testid="user">{JSON.stringify(user)}</span>
      <span data-testid="role">{role ?? "null"}</span>
      <span data-testid="isSuperAdmin">{String(isSuperAdmin)}</span>
      <button data-testid="logout-btn" onClick={logout}>
        Logout
      </button>
      <button data-testid="checkAuth-btn" onClick={checkAuth}>
        Check Auth
      </button>
      <button data-testid="refreshUser-btn" onClick={refreshUser}>
        Refresh User
      </button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mocks
    vi.mocked(authLib.isAuthenticated).mockReturnValue(false);
    vi.mocked(authLib.getUserData).mockReturnValue(null);
    vi.mocked(authLib.getRemainingSessionTime).mockReturnValue(30 * 60 * 1000);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // =====================
  // Initial State Tests
  // =====================
  describe("Initial State", () => {
    it("should show children after initial auth check", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <div data-testid="child">Child content</div>
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("child")).toBeInTheDocument();
      });
    });

    it("should have isAuth=false when not authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("false");
      });
    });

    it("should have user=null when not authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);
      vi.mocked(authLib.getUserData).mockReturnValue(null);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("null");
      });
    });

    it("should have role=null when not authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("null");
      });
    });
  });

  // =====================
  // Authenticated State Tests
  // =====================
  describe("Authenticated State", () => {
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      profile: {
        organization: 1,
        organization_name: "Test Org",
        role: "admin" as const,
        is_super_admin: false,
      },
    };

    it("should have isAuth=true when authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });
    });

    it("should load user data when authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        const userText = screen.getByTestId("user").textContent;
        expect(userText).toContain("testuser");
      });
    });

    it("should derive role from user profile", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("admin");
      });
    });

    it("should derive manager role correctly", async () => {
      const managerUser = {
        ...mockUser,
        profile: { ...mockUser.profile, role: "manager" as const },
      };
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(managerUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("manager");
      });
    });

    it("should derive viewer role correctly", async () => {
      const viewerUser = {
        ...mockUser,
        profile: { ...mockUser.profile, role: "viewer" as const },
      };
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(viewerUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("viewer");
      });
    });

    it("should have isSuperAdmin=false for regular users", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("false");
      });
    });

    it("should have isSuperAdmin=true for super admins", async () => {
      const superAdminUser = {
        ...mockUser,
        profile: { ...mockUser.profile, is_super_admin: true },
      };
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(superAdminUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("true");
      });
    });
  });

  // =====================
  // Logout Tests
  // =====================
  describe("Logout", () => {
    const mockUser = {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      profile: {
        organization: 1,
        organization_name: "Test Org",
        role: "admin" as const,
        is_super_admin: false,
      },
    };

    it("should call authAPI.logout when logging out", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);
      vi.mocked(api.authAPI.logout).mockResolvedValue({ data: {} } as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByTestId("logout-btn").click();
      });

      expect(api.authAPI.logout).toHaveBeenCalled();
    });

    it("should clear session after logout", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);
      vi.mocked(api.authAPI.logout).mockResolvedValue({ data: {} } as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByTestId("logout-btn").click();
      });

      expect(authLib.clearSession).toHaveBeenCalled();
    });

    it("should set isAuth=false after logout", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);
      vi.mocked(api.authAPI.logout).mockResolvedValue({ data: {} } as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByTestId("logout-btn").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("false");
      });
    });

    it("should set user=null after logout", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);
      vi.mocked(api.authAPI.logout).mockResolvedValue({ data: {} } as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("testuser");
      });

      await act(async () => {
        screen.getByTestId("logout-btn").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("null");
      });
    });

    it("should still clear session if server logout fails", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(mockUser);
      vi.mocked(api.authAPI.logout).mockRejectedValue(
        new Error("Network error"),
      );

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByTestId("logout-btn").click();
      });

      expect(authLib.clearSession).toHaveBeenCalled();
    });
  });

  // =====================
  // checkAuth Tests
  // =====================
  describe("checkAuth", () => {
    it("should update isAuth based on isAuthenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("false");
      });

      // Now simulate becoming authenticated
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue({
        id: 1,
        username: "test",
        email: "test@test.com",
        profile: {
          organization: 1,
          role: "viewer" as const,
          is_super_admin: false,
        },
      });

      await act(async () => {
        screen.getByTestId("checkAuth-btn").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("isAuth")).toHaveTextContent("true");
      });
    });

    it("should clear user when not authenticated", async () => {
      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue({
        id: 1,
        username: "test",
        email: "test@test.com",
        profile: {
          organization: 1,
          role: "viewer" as const,
          is_super_admin: false,
        },
      });

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("test");
      });

      // Now simulate session expiring
      vi.mocked(authLib.isAuthenticated).mockReturnValue(false);

      await act(async () => {
        screen.getByTestId("checkAuth-btn").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("null");
      });
    });
  });

  // =====================
  // refreshUser Tests
  // =====================
  describe("refreshUser", () => {
    it("should reload user data from localStorage", async () => {
      const initialUser = {
        id: 1,
        username: "initial",
        email: "initial@test.com",
        profile: {
          organization: 1,
          role: "viewer" as const,
          is_super_admin: false,
        },
      };
      const updatedUser = {
        id: 1,
        username: "updated",
        email: "updated@test.com",
        profile: {
          organization: 1,
          role: "admin" as const,
          is_super_admin: true,
        },
      };

      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(initialUser);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("initial");
      });

      // Update the mock to return new user data
      vi.mocked(authLib.getUserData).mockReturnValue(updatedUser);

      await act(async () => {
        screen.getByTestId("refreshUser-btn").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("updated");
      });
    });
  });

  // =====================
  // useAuth Hook Tests
  // =====================
  describe("useAuth Hook", () => {
    it("should throw error when used outside provider", () => {
      // Suppress console.error for this test
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      expect(() => {
        render(<TestConsumer />);
      }).toThrow("useAuth must be used within an AuthProvider");

      consoleSpy.mockRestore();
    });
  });

  // =====================
  // Edge Cases
  // =====================
  describe("Edge Cases", () => {
    it("should handle user without profile", async () => {
      const userNoProfile = {
        id: 1,
        username: "test",
        email: "test@test.com",
      };

      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(userNoProfile as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("null");
        expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("false");
      });
    });

    it("should handle profile without role", async () => {
      const userNoRole = {
        id: 1,
        username: "test",
        email: "test@test.com",
        profile: { organization: 1, is_super_admin: false },
      };

      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(userNoRole as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("role")).toHaveTextContent("null");
      });
    });

    it("should handle profile without is_super_admin field", async () => {
      const userNoSuperAdmin = {
        id: 1,
        username: "test",
        email: "test@test.com",
        profile: { organization: 1, role: "admin" as const },
      };

      vi.mocked(authLib.isAuthenticated).mockReturnValue(true);
      vi.mocked(authLib.getUserData).mockReturnValue(userNoSuperAdmin as any);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("isSuperAdmin")).toHaveTextContent("false");
      });
    });
  });
});
