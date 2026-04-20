/**
 * Organization Context for multi-organization access
 *
 * Supports:
 * - Superusers: Can switch to any organization
 * - Multi-org users: Can switch between organizations they have memberships in
 * - Single-org users: Default to their only organization (no switching)
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "./AuthContext";
import { api, Organization, OrganizationMembership, UserRole } from "@/lib/api";

interface OrganizationContextType {
  /** Currently active organization (defaults to user's primary org) */
  activeOrganization: Organization | null;
  /** User's primary organization */
  userOrganization: Organization | null;
  /** List of organizations user can access */
  organizations: Organization[];
  /** User's role in the active organization */
  activeRole: UserRole | null;
  /** Whether the user can switch organizations (superuser or multi-org user) */
  canSwitch: boolean;
  /** Whether the user is a multi-org user (has memberships in multiple orgs) */
  isMultiOrgUser: boolean;
  /** Whether we're viewing a different org than user's primary */
  isViewingOtherOrg: boolean;
  /** Loading state */
  isLoading: boolean;
  /** Switch to a different organization */
  switchOrganization: (orgId: number) => void;
  /** Reset to user's primary organization */
  resetToDefault: () => void;
  /** Get user's role in a specific organization */
  getRoleInOrg: (orgId: number) => UserRole | null;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(
  undefined,
);

const STORAGE_KEY = "active_organization_id";

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const { user, isSuperAdmin, isAuth } = useAuth();
  const queryClient = useQueryClient();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [activeOrganization, setActiveOrganization] =
    useState<Organization | null>(null);
  const [userOrganization, setUserOrganization] = useState<Organization | null>(
    null,
  );
  const [activeRole, setActiveRole] = useState<UserRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Track if we've already initialized to prevent duplicate fetches
  const initializedRef = useRef(false);
  const lastUserIdRef = useRef<number | null>(null);

  // Check if user has multiple org memberships (from profile.organizations)
  const isMultiOrgUser = (user?.profile?.organizations?.length ?? 0) > 1;

  // Determine if user can switch organizations (superuser OR multi-org user)
  const canSwitch =
    (isSuperAdmin || isMultiOrgUser) && organizations.length > 1;

  // Check if viewing a different org than primary
  const isViewingOtherOrg =
    activeOrganization !== null &&
    userOrganization !== null &&
    activeOrganization.id !== userOrganization.id;

  // Get role in a specific organization
  const getRoleInOrg = useCallback(
    (orgId: number): UserRole | null => {
      // For superusers, they always have admin access
      if (isSuperAdmin) return "admin";
      // Look up from memberships
      const membership = memberships.find((m) => m.organization === orgId);
      return membership?.role ?? null;
    },
    [isSuperAdmin, memberships],
  );

  /**
   * Initialize organization state - runs once per user session
   */
  useEffect(() => {
    const initializeOrganizations = async () => {
      // Skip if not authenticated
      if (!isAuth || !user) {
        setIsLoading(false);
        return;
      }

      // Skip if already initialized for this user
      const userId = user.id;
      if (initializedRef.current && lastUserIdRef.current === userId) {
        return;
      }

      // Mark as initializing
      initializedRef.current = true;
      lastUserIdRef.current = userId;
      setIsLoading(true);

      try {
        // Check for multi-org memberships in user profile
        const userMemberships = user.profile?.organizations ?? [];
        setMemberships(userMemberships);

        // Find user's primary organization
        const primaryMembership = userMemberships.find((m) => m.is_primary);
        const userOrg: Organization | null = primaryMembership
          ? {
              id: primaryMembership.organization,
              name: primaryMembership.organization_name,
              slug: primaryMembership.organization_slug,
              description: "",
              is_active: true,
              is_demo: primaryMembership.organization_is_demo,
              created_at: "",
            }
          : user.profile?.organization
            ? {
                id: user.profile.organization,
                name: user.profile.organization_name || "Unknown",
                slug: "",
                description: "",
                is_active: true,
                is_demo: user.profile?.organization_is_demo ?? false,
                created_at: "",
              }
            : null;

        setUserOrganization(userOrg);

        // For superusers, fetch all organizations
        if (isSuperAdmin) {
          try {
            const response = await api.get("/auth/organizations/");
            const allOrgs = (response.data.results ??
              response.data) as Organization[];
            setOrganizations(allOrgs);

            // Check for persisted organization selection
            const storedOrgId = localStorage.getItem(STORAGE_KEY);
            if (storedOrgId) {
              const storedOrg = allOrgs.find(
                (org) => org.id === parseInt(storedOrgId, 10),
              );
              if (storedOrg) {
                setActiveOrganization(storedOrg);
                setActiveRole("admin"); // Superusers always admin
              } else {
                localStorage.removeItem(STORAGE_KEY);
                setActiveOrganization(userOrg);
                setActiveRole(user.profile?.role ?? null);
              }
            } else {
              setActiveOrganization(userOrg);
              setActiveRole(user.profile?.role ?? null);
            }
          } catch {
            setOrganizations(userOrg ? [userOrg] : []);
            setActiveOrganization(userOrg);
            setActiveRole(user.profile?.role ?? null);
          }
        } else if (userMemberships.length > 1) {
          // Multi-org user: build org list from memberships
          const memberOrgs: Organization[] = userMemberships.map((m) => ({
            id: m.organization,
            name: m.organization_name,
            slug: m.organization_slug,
            description: "",
            is_active: true,
            is_demo: m.organization_is_demo,
            created_at: "",
          }));
          setOrganizations(memberOrgs);

          // Check for persisted organization selection
          const storedOrgId = localStorage.getItem(STORAGE_KEY);
          if (storedOrgId) {
            const storedMembership = userMemberships.find(
              (m) => m.organization === parseInt(storedOrgId, 10),
            );
            if (storedMembership) {
              const storedOrg = memberOrgs.find(
                (org) => org.id === parseInt(storedOrgId, 10),
              );
              setActiveOrganization(storedOrg ?? userOrg);
              setActiveRole(storedMembership.role);
            } else {
              localStorage.removeItem(STORAGE_KEY);
              setActiveOrganization(userOrg);
              setActiveRole(
                primaryMembership?.role ?? user.profile?.role ?? null,
              );
            }
          } else {
            setActiveOrganization(userOrg);
            setActiveRole(
              primaryMembership?.role ?? user.profile?.role ?? null,
            );
          }
        } else {
          // Single-org user
          setOrganizations(userOrg ? [userOrg] : []);
          setActiveOrganization(userOrg);
          setActiveRole(user.profile?.role ?? null);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initializeOrganizations();
  }, [isAuth, user, isSuperAdmin]);

  /**
   * Clear organization state on logout
   */
  useEffect(() => {
    if (!isAuth) {
      setOrganizations([]);
      setMemberships([]);
      setActiveOrganization(null);
      setUserOrganization(null);
      setActiveRole(null);
      localStorage.removeItem(STORAGE_KEY);
      // Reset initialization tracking so next login re-fetches
      initializedRef.current = false;
      lastUserIdRef.current = null;
    }
  }, [isAuth]);

  /**
   * Switch to a different organization
   */
  const switchOrganization = useCallback(
    (orgId: number) => {
      if (!canSwitch) return;

      const newOrg = organizations.find((org) => org.id === orgId);
      if (!newOrg) return;

      // Get the new role for this org
      const newRole = getRoleInOrg(orgId);

      setActiveOrganization(newOrg);
      setActiveRole(newRole);
      localStorage.setItem(STORAGE_KEY, String(orgId));

      // Invalidate all queries to refetch with new organization
      queryClient.invalidateQueries();

      // Dispatch custom event for any listeners
      window.dispatchEvent(
        new CustomEvent("organizationChanged", {
          detail: {
            organizationId: orgId,
            organization: newOrg,
            role: newRole,
          },
        }),
      );
    },
    [canSwitch, organizations, queryClient, getRoleInOrg],
  );

  /**
   * Reset to user's primary organization
   */
  const resetToDefault = useCallback(() => {
    if (!userOrganization) return;

    // Get user's role in their primary org
    const primaryRole = getRoleInOrg(userOrganization.id);

    setActiveOrganization(userOrganization);
    setActiveRole(primaryRole);
    localStorage.removeItem(STORAGE_KEY);

    // Invalidate all queries to refetch with user's organization
    queryClient.invalidateQueries();

    // Dispatch custom event
    window.dispatchEvent(
      new CustomEvent("organizationChanged", {
        detail: {
          organizationId: userOrganization.id,
          organization: userOrganization,
          role: primaryRole,
        },
      }),
    );
  }, [userOrganization, queryClient, getRoleInOrg]);

  return (
    <OrganizationContext.Provider
      value={{
        activeOrganization,
        userOrganization,
        organizations,
        activeRole,
        canSwitch,
        isMultiOrgUser,
        isViewingOtherOrg,
        isLoading,
        switchOrganization,
        resetToDefault,
        getRoleInOrg,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error(
      "useOrganization must be used within an OrganizationProvider",
    );
  }
  return context;
}

/**
 * Helper to get organization_id parameter for API calls
 * Returns empty object if viewing user's own org (default behavior)
 */
export function getOrganizationParam(): { organization_id?: number } {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? { organization_id: parseInt(stored, 10) } : {};
}
