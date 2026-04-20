/**
 * Permission Context
 *
 * Provides centralized permission checking throughout the application.
 * Uses the PERMISSION_MATRIX as the single source of truth for role permissions.
 *
 * Usage:
 * ```tsx
 * const { hasPermission, isAtLeast, role } = usePermissions();
 *
 * if (hasPermission('delete')) {
 *   // Show delete button
 * }
 *
 * if (isAtLeast('manager')) {
 *   // Show manager+ features
 * }
 * ```
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useAuth } from "./AuthContext";
import type { UserRole } from "@/lib/api";
import {
  type Permission,
  PERMISSION_MATRIX,
  PERMISSION_DENIAL_MESSAGES,
  ROLE_HIERARCHY,
} from "@/types/permissions";

/**
 * Permission context value interface
 */
interface PermissionContextType {
  /** Current user's role (null if not authenticated) */
  role: UserRole | null;

  /** Check if user has a specific permission */
  hasPermission: (permission: Permission) => boolean;

  /** Check if user has ALL of the specified permissions */
  hasAllPermissions: (permissions: Permission[]) => boolean;

  /** Check if user has ANY of the specified permissions */
  hasAnyPermission: (permissions: Permission[]) => boolean;

  /** Get the denial message for a permission */
  getDenialMessage: (permission: Permission) => string;

  /** Check if user's role is at least the specified level */
  isAtLeast: (minRole: UserRole) => boolean;

  /** Check if user is an admin */
  isAdmin: boolean;

  /** Check if user is a manager or higher */
  isManagerOrAbove: boolean;

  /** Check if user is a super admin (Django superuser with platform-level privileges) */
  isSuperAdmin: boolean;

  /** Check if user can upload data for any organization (super admins only) */
  canUploadForAnyOrg: boolean;
}

const PermissionContext = createContext<PermissionContextType | undefined>(
  undefined,
);

interface PermissionProviderProps {
  children: ReactNode;
}

/**
 * Permission Provider Component
 *
 * Wraps the application to provide permission checking capabilities.
 * Must be nested inside AuthProvider to access user role.
 */
export function PermissionProvider({ children }: PermissionProviderProps) {
  const { role, isSuperAdmin } = useAuth();

  const value = useMemo<PermissionContextType>(() => {
    /**
     * Check if user has a specific permission
     */
    const hasPermission = (permission: Permission): boolean => {
      if (!role) return false;
      return PERMISSION_MATRIX[role].includes(permission);
    };

    /**
     * Check if user has ALL specified permissions
     */
    const hasAllPermissions = (permissions: Permission[]): boolean => {
      if (!role) return false;
      return permissions.every((p) => PERMISSION_MATRIX[role].includes(p));
    };

    /**
     * Check if user has ANY of the specified permissions
     */
    const hasAnyPermission = (permissions: Permission[]): boolean => {
      if (!role) return false;
      return permissions.some((p) => PERMISSION_MATRIX[role].includes(p));
    };

    /**
     * Get the denial message for a permission
     */
    const getDenialMessage = (permission: Permission): string => {
      return PERMISSION_DENIAL_MESSAGES[permission];
    };

    /**
     * Check if user's role is at least the specified level
     */
    const isAtLeast = (minRole: UserRole): boolean => {
      if (!role) return false;
      const currentLevel = ROLE_HIERARCHY.indexOf(role);
      const minLevel = ROLE_HIERARCHY.indexOf(minRole);
      return currentLevel >= minLevel;
    };

    return {
      role,
      hasPermission,
      hasAllPermissions,
      hasAnyPermission,
      getDenialMessage,
      isAtLeast,
      isAdmin: role === "admin",
      isManagerOrAbove: isAtLeast("manager"),
      isSuperAdmin,
      canUploadForAnyOrg: isSuperAdmin,
    };
  }, [role, isSuperAdmin]);

  return (
    <PermissionContext.Provider value={value}>
      {children}
    </PermissionContext.Provider>
  );
}

/**
 * Hook to access permission context
 *
 * @throws Error if used outside PermissionProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { hasPermission, isAdmin } = usePermissions();
 *
 *   return (
 *     <div>
 *       {hasPermission('upload') && <UploadButton />}
 *       {isAdmin && <AdminSettings />}
 *     </div>
 *   );
 * }
 * ```
 */
export function usePermissions(): PermissionContextType {
  const context = useContext(PermissionContext);
  if (context === undefined) {
    throw new Error("usePermissions must be used within a PermissionProvider");
  }
  return context;
}

/**
 * Convenience hook for checking a single permission
 *
 * @param permission - The permission to check
 * @returns True if user has the permission
 *
 * @example
 * ```tsx
 * const canUpload = useHasPermission('upload');
 * ```
 */
export function useHasPermission(permission: Permission): boolean {
  const { hasPermission } = usePermissions();
  return hasPermission(permission);
}

/**
 * Convenience hook for checking admin status
 *
 * @returns True if user is an admin
 */
export function useIsAdmin(): boolean {
  const { isAdmin } = usePermissions();
  return isAdmin;
}
