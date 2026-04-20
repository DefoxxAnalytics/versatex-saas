/**
 * Permission Types and Constants
 *
 * This file serves as the single source of truth for all RBAC-related
 * type definitions and permission mappings in the frontend.
 *
 * Mirrors backend permission model from:
 * - backend/apps/authentication/models.py (UserProfile.can_upload_data, can_delete_data, etc.)
 * - backend/apps/authentication/permissions.py (IsAdmin, IsManager, CanUploadData, etc.)
 */

import type { UserRole } from "@/lib/api";

/**
 * All available permissions in the application.
 * Maps directly to backend permission methods.
 *
 * Note: 'upload' permission is now handled via Django Admin Panel.
 * Frontend no longer has upload functionality - it's a read-only analytics dashboard.
 */
export type Permission =
  | "view" // All authenticated users can view data
  | "upload" // Upload procurement data via Admin Panel (Admin, Manager)
  | "export" // Export data to CSV/Excel (Admin, Manager)
  | "delete" // Delete individual transactions (Admin only)
  | "clear" // Clear all data (Admin only)
  | "admin_panel"; // Access Django admin panel (Admin only)

/**
 * Permission matrix defining which roles have which permissions.
 * This is the single source of truth - mirrors backend logic.
 *
 * Backend reference:
 * - admin: can_upload_data=True, can_delete_data=True
 * - manager: can_upload_data=True, can_delete_data=False
 * - viewer: can_upload_data=False, can_delete_data=False
 */
export const PERMISSION_MATRIX: Record<UserRole, Permission[]> = {
  admin: ["view", "upload", "export", "delete", "clear", "admin_panel"],
  manager: ["view", "upload", "export"],
  viewer: ["view"],
} as const;

/**
 * Human-readable labels for each permission.
 * Used for accessibility and UI display.
 */
export const PERMISSION_LABELS: Record<Permission, string> = {
  view: "View data and analytics",
  upload: "Upload procurement data",
  export: "Export data to CSV/Excel",
  delete: "Delete transactions",
  clear: "Clear all data",
  admin_panel: "Access admin panel",
} as const;

/**
 * Denial messages shown when user lacks a permission.
 * These are displayed in tooltips and toast notifications.
 */
export const PERMISSION_DENIAL_MESSAGES: Record<Permission, string> = {
  view: "You do not have permission to view this content",
  upload:
    "Data upload is available via the Admin Panel for Managers and Admins",
  export: "Only Managers and Admins can export data",
  delete: "Only Admins can delete transactions",
  clear: "Only Admins can clear all data",
  admin_panel: "Only Admins can access the admin panel",
} as const;

/**
 * Role hierarchy for comparison operations.
 * Higher index = more permissions.
 *
 * viewer (0) < manager (1) < admin (2)
 */
export const ROLE_HIERARCHY: readonly UserRole[] = [
  "viewer",
  "manager",
  "admin",
] as const;

/**
 * Check if a role has a specific permission.
 * Pure function for use outside of React context.
 *
 * @param role - The user's role
 * @param permission - The permission to check
 * @returns True if the role has the permission
 */
export function roleHasPermission(
  role: UserRole | null,
  permission: Permission,
): boolean {
  if (!role) return false;
  return PERMISSION_MATRIX[role].includes(permission);
}

/**
 * Check if a role is at least a certain level in the hierarchy.
 * Pure function for use outside of React context.
 *
 * @param role - The user's role
 * @param minRole - The minimum required role
 * @returns True if role >= minRole in hierarchy
 */
export function roleIsAtLeast(
  role: UserRole | null,
  minRole: UserRole,
): boolean {
  if (!role) return false;
  const currentLevel = ROLE_HIERARCHY.indexOf(role);
  const minLevel = ROLE_HIERARCHY.indexOf(minRole);
  return currentLevel >= minLevel;
}
