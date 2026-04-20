/**
 * RoleGuard Component
 *
 * Route-level protection component that restricts access based on user permissions.
 * Redirects unauthorized users to a specified route with an optional toast notification.
 *
 * Usage:
 * ```tsx
 * // Require specific permission
 * <RoleGuard requires="admin_panel">
 *   <AdminSettings />
 * </RoleGuard>
 *
 * // Require minimum role level
 * <RoleGuard minRole="manager">
 *   <ManagerDashboard />
 * </RoleGuard>
 *
 * // Multiple permissions (all required)
 * <RoleGuard requires={['upload', 'delete']}>
 *   <DataManagement />
 * </RoleGuard>
 *
 * // Custom redirect and no toast
 * <RoleGuard requires="admin_panel" redirectTo="/settings" showToast={false}>
 *   <AdminPanel />
 * </RoleGuard>
 * ```
 */

import { type ReactNode, useEffect, useRef } from "react";
import { Redirect, useLocation } from "wouter";
import { toast } from "sonner";
import { usePermissions } from "@/contexts/PermissionContext";
import type { Permission } from "@/types/permissions";
import type { UserRole } from "@/lib/api";

interface RoleGuardProps {
  /** Content to render if user has permission */
  children: ReactNode;

  /** Required permission(s) - user must have ALL specified permissions */
  requires?: Permission | Permission[];

  /** Minimum role level required */
  minRole?: UserRole;

  /** Where to redirect unauthorized users (default: '/') */
  redirectTo?: string;

  /** Custom fallback component instead of redirect */
  fallback?: ReactNode;

  /** Whether to show toast notification on denial (default: true) */
  showToast?: boolean;

  /** Custom denial message (overrides default) */
  denialMessage?: string;
}

/**
 * RoleGuard Component
 *
 * Protects routes by checking user permissions before rendering children.
 * If user lacks permission, redirects to specified route with optional toast.
 */
export function RoleGuard({
  children,
  requires,
  minRole,
  redirectTo = "/",
  fallback,
  showToast = true,
  denialMessage,
}: RoleGuardProps) {
  const { hasPermission, hasAllPermissions, isAtLeast, getDenialMessage } =
    usePermissions();
  const [location] = useLocation();
  const hasShownToast = useRef(false);

  // Determine if user has access
  let hasAccess = true;
  let denialReason =
    denialMessage || "You do not have permission to access this page";

  // Check minimum role requirement
  if (minRole && !isAtLeast(minRole)) {
    hasAccess = false;
    denialReason =
      denialMessage || `This page requires ${minRole} role or higher`;
  }

  // Check specific permission requirement
  if (requires) {
    const permissions = Array.isArray(requires) ? requires : [requires];
    if (!hasAllPermissions(permissions)) {
      hasAccess = false;
      denialReason = denialMessage || getDenialMessage(permissions[0]);
    }
  }

  // Show toast notification on first denial (avoid duplicates on re-renders)
  useEffect(() => {
    if (
      !hasAccess &&
      showToast &&
      !hasShownToast.current &&
      location !== redirectTo
    ) {
      toast.error(denialReason, { id: "role-guard-denial" });
      hasShownToast.current = true;
    }
  }, [hasAccess, showToast, denialReason, location, redirectTo]);

  // Reset toast flag when access status changes
  useEffect(() => {
    if (hasAccess) {
      hasShownToast.current = false;
    }
  }, [hasAccess]);

  // User lacks permission
  if (!hasAccess) {
    // Return custom fallback if provided
    if (fallback) {
      return <>{fallback}</>;
    }

    // Redirect to specified route
    return <Redirect to={redirectTo} />;
  }

  // User has permission - render children
  return <>{children}</>;
}

/**
 * Convenience component for admin-only routes
 */
export function AdminRoute({
  children,
  redirectTo = "/",
  showToast = true,
  fallback,
}: Omit<RoleGuardProps, "requires" | "minRole">) {
  return (
    <RoleGuard
      requires="admin_panel"
      redirectTo={redirectTo}
      showToast={showToast}
      fallback={fallback}
    >
      {children}
    </RoleGuard>
  );
}

/**
 * Convenience component for manager+ routes
 */
export function ManagerRoute({
  children,
  redirectTo = "/",
  showToast = true,
  fallback,
}: Omit<RoleGuardProps, "requires" | "minRole">) {
  return (
    <RoleGuard
      minRole="manager"
      redirectTo={redirectTo}
      showToast={showToast}
      fallback={fallback}
    >
      {children}
    </RoleGuard>
  );
}
