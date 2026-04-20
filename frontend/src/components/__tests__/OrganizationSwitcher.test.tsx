/**
 * Tests for OrganizationSwitcher component
 *
 * Tests the multi-org user organization switching functionality.
 * Note: Radix UI dropdowns render in portals, so we test the trigger button
 * and mock the context functions directly.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OrganizationSwitcher } from "../OrganizationSwitcher";
import * as OrganizationContext from "@/contexts/OrganizationContext";
import * as AuthContext from "@/contexts/AuthContext";

// Mock organization context
vi.mock("@/contexts/OrganizationContext", async () => {
  const actual = await vi.importActual("@/contexts/OrganizationContext");
  return {
    ...actual,
    useOrganization: vi.fn(),
  };
});

// Mock auth context
vi.mock("@/contexts/AuthContext", async () => {
  const actual = await vi.importActual("@/contexts/AuthContext");
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

// Test wrapper with QueryClient
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

describe("OrganizationSwitcher", () => {
  const mockSwitchOrganization = vi.fn();
  const mockResetToDefault = vi.fn();
  const mockGetRoleInOrg = vi.fn();

  const mockOrganizations = [
    {
      id: 1,
      name: "Test Organization",
      slug: "test-org",
      description: "",
      is_active: true,
      is_demo: false,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      name: "Second Org",
      slug: "second-org",
      description: "",
      is_active: true,
      is_demo: false,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 3,
      name: "Third Org",
      slug: "third-org",
      description: "",
      is_active: true,
      is_demo: false,
      created_at: "2024-01-01T00:00:00Z",
    },
  ];

  const defaultOrgContextValue = {
    activeOrganization: mockOrganizations[0],
    userOrganization: mockOrganizations[0],
    organizations: mockOrganizations,
    activeRole: "admin" as const,
    canSwitch: true,
    isMultiOrgUser: true,
    isViewingOtherOrg: false,
    isLoading: false,
    switchOrganization: mockSwitchOrganization,
    resetToDefault: mockResetToDefault,
    getRoleInOrg: mockGetRoleInOrg,
  };

  const defaultAuthContextValue = {
    isAuth: true,
    isSuperAdmin: false,
    user: {
      id: 1,
      username: "testuser",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      profile: {
        id: 1,
        organization: 1,
        organization_name: "Test Organization",
        role: "admin" as const,
        phone: "",
        department: "",
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
        is_super_admin: false,
      },
    },
    role: "admin" as const,
    logout: vi.fn(),
    checkAuth: vi.fn(),
    refreshUser: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetRoleInOrg.mockImplementation((orgId: number) => {
      if (orgId === 1) return "admin";
      if (orgId === 2) return "manager";
      if (orgId === 3) return "viewer";
      return null;
    });

    vi.mocked(OrganizationContext.useOrganization).mockReturnValue(
      defaultOrgContextValue,
    );
    vi.mocked(AuthContext.useAuth).mockReturnValue(defaultAuthContextValue);
  });

  it("should not render when canSwitch is false", () => {
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      ...defaultOrgContextValue,
      canSwitch: false,
    });

    const { container } = render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });

  it("should not render when loading", () => {
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      ...defaultOrgContextValue,
      isLoading: true,
    });

    const { container } = render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });

  it("should render organization switcher when canSwitch is true", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    // Should show the current organization name in button
    expect(screen.getByText("Test Organization")).toBeInTheDocument();
  });

  it("should show trigger button with current org name", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    const triggerButton = screen.getByRole("button");
    expect(triggerButton).toBeInTheDocument();
    expect(screen.getByText("Test Organization")).toBeInTheDocument();
  });

  it("should apply amber styles when viewing other org", () => {
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      ...defaultOrgContextValue,
      isViewingOtherOrg: true,
      activeOrganization: mockOrganizations[1],
    });

    render(<OrganizationSwitcher colorScheme="navy" />, {
      wrapper: createWrapper(),
    });

    const button = screen.getByRole("button");
    // Should have amber styling when viewing other org
    expect(button.className).toContain("amber");
  });

  it('should show "Select Org" when no active organization', () => {
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      ...defaultOrgContextValue,
      activeOrganization: null,
    });

    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Select Org")).toBeInTheDocument();
  });

  it("should apply classic color scheme styles", () => {
    render(<OrganizationSwitcher colorScheme="classic" />, {
      wrapper: createWrapper(),
    });

    const button = screen.getByRole("button");
    // Classic scheme should have different text color
    expect(button.className).toContain("text-gray-700");
  });

  it("should apply navy color scheme styles", () => {
    render(<OrganizationSwitcher colorScheme="navy" />, {
      wrapper: createWrapper(),
    });

    const button = screen.getByRole("button");
    // Navy scheme should have white text
    expect(button.className).toContain("text-white");
  });

  it("should have dropdown trigger functionality", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    const triggerButton = screen.getByRole("button");
    // Radix UI dropdown trigger should have aria attributes
    expect(triggerButton).toHaveAttribute("type", "button");
  });

  it("should display icons in button", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    // lucide-react icons render as SVG elements
    const button = screen.getByRole("button");
    const svgs = button.querySelectorAll("svg");
    // Should have at least 2 icons (Building2 and ChevronDown)
    expect(svgs.length).toBeGreaterThanOrEqual(2);
  });

  it("should apply amber ring to trigger when active organization is demo", () => {
    // #given an active organization flagged as demo data
    const demoOrg = { ...mockOrganizations[0], is_demo: true };
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      ...defaultOrgContextValue,
      activeOrganization: demoOrg,
      userOrganization: demoOrg,
      organizations: [demoOrg, ...mockOrganizations.slice(1)],
    });

    // #when the switcher renders
    render(<OrganizationSwitcher />, { wrapper: createWrapper() });

    // #then the trigger button carries the amber demo ring
    const button = screen.getByRole("button");
    expect(button.className).toContain("ring-amber-400");
  });

  it("should not apply the demo ring when active organization is not demo", () => {
    // #given the default (non-demo) active org from the shared fixture
    render(<OrganizationSwitcher />, { wrapper: createWrapper() });

    // #when we inspect the trigger
    const button = screen.getByRole("button");

    // #then the amber demo ring class is absent
    expect(button.className).not.toContain("ring-amber-400");
  });
});

describe("OrganizationSwitcher - Single Org User", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Single org user - canSwitch should be false
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      activeOrganization: {
        id: 1,
        name: "Only Org",
        slug: "only-org",
        description: "",
        is_active: true,
        is_demo: false,
        created_at: "2024-01-01T00:00:00Z",
      },
      userOrganization: {
        id: 1,
        name: "Only Org",
        slug: "only-org",
        description: "",
        is_active: true,
        is_demo: false,
        created_at: "2024-01-01T00:00:00Z",
      },
      organizations: [
        {
          id: 1,
          name: "Only Org",
          slug: "only-org",
          description: "",
          is_active: true,
          is_demo: false,
          created_at: "2024-01-01T00:00:00Z",
        },
      ],
      activeRole: "viewer" as const,
      canSwitch: false,
      isMultiOrgUser: false,
      isViewingOtherOrg: false,
      isLoading: false,
      switchOrganization: vi.fn(),
      resetToDefault: vi.fn(),
      getRoleInOrg: vi.fn(),
    });

    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuth: true,
      isSuperAdmin: false,
      user: {
        id: 1,
        username: "singleuser",
        email: "single@example.com",
        first_name: "Single",
        last_name: "User",
        profile: {
          id: 1,
          organization: 1,
          organization_name: "Only Org",
          role: "viewer" as const,
          phone: "",
          department: "",
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          is_super_admin: false,
        },
      },
      role: "viewer" as const,
      logout: vi.fn(),
      checkAuth: vi.fn(),
      refreshUser: vi.fn(),
    });
  });

  it("should not render for single org user", () => {
    const { container } = render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });
});

describe("OrganizationSwitcher - Superuser", () => {
  const mockSwitchOrganization = vi.fn();
  const mockResetToDefault = vi.fn();
  const mockGetRoleInOrg = vi.fn();

  const mockOrganizations = [
    {
      id: 1,
      name: "Org A",
      slug: "org-a",
      description: "",
      is_active: true,
      is_demo: false,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      name: "Org B",
      slug: "org-b",
      description: "",
      is_active: true,
      is_demo: false,
      created_at: "2024-01-01T00:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    // Superuser mock - can see all orgs
    vi.mocked(OrganizationContext.useOrganization).mockReturnValue({
      activeOrganization: mockOrganizations[0],
      userOrganization: mockOrganizations[0],
      organizations: mockOrganizations,
      activeRole: "admin" as const,
      canSwitch: true,
      isMultiOrgUser: false, // Superuser may not be "multi-org" but can switch
      isViewingOtherOrg: false,
      isLoading: false,
      switchOrganization: mockSwitchOrganization,
      resetToDefault: mockResetToDefault,
      getRoleInOrg: mockGetRoleInOrg,
    });

    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuth: true,
      isSuperAdmin: true,
      user: {
        id: 1,
        username: "superadmin",
        email: "super@example.com",
        first_name: "Super",
        last_name: "Admin",
        profile: {
          id: 1,
          organization: 1,
          organization_name: "Org A",
          role: "admin" as const,
          phone: "",
          department: "",
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          is_super_admin: true,
        },
      },
      role: "admin" as const,
      logout: vi.fn(),
      checkAuth: vi.fn(),
      refreshUser: vi.fn(),
    });

    mockGetRoleInOrg.mockReturnValue(null); // Superuser has access but no specific role
  });

  it("should render for superuser with canSwitch true", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Org A")).toBeInTheDocument();
  });

  it("should render trigger button for superuser", () => {
    render(<OrganizationSwitcher />, {
      wrapper: createWrapper(),
    });

    const triggerButton = screen.getByRole("button");
    expect(triggerButton).toBeInTheDocument();
  });
});
