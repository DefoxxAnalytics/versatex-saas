/**
 * PermissionGate Component
 *
 * UI-level conditional rendering based on user permissions.
 * Provides two behaviors:
 * - 'hide': Completely removes unauthorized content from DOM
 * - 'disable': Renders disabled state with tooltip explaining why
 *
 * Usage:
 * ```tsx
 * // Hide content for unauthorized users (default)
 * <PermissionGate requires="delete">
 *   <DeleteButton />
 * </PermissionGate>
 *
 * // Disable with tooltip for unauthorized users
 * <PermissionGate requires="upload" behavior="disable">
 *   <UploadButton />
 * </PermissionGate>
 *
 * // Custom tooltip message
 * <PermissionGate
 *   requires="export"
 *   behavior="disable"
 *   tooltip="Upgrade to Manager to export data"
 * >
 *   <ExportButton />
 * </PermissionGate>
 * ```
 */

import {
  type ReactNode,
  cloneElement,
  isValidElement,
  type ReactElement,
} from "react";
import { usePermissions } from "@/contexts/PermissionContext";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { Permission } from "@/types/permissions";

type GateBehavior = "hide" | "disable";

interface PermissionGateProps {
  /** Content to render/protect */
  children: ReactNode;

  /** Required permission(s) to show/enable content */
  requires: Permission | Permission[];

  /** Behavior when permission denied: 'hide' removes element, 'disable' shows disabled state */
  behavior?: GateBehavior;

  /** Custom tooltip message (overrides default denial message) */
  tooltip?: string;

  /** Fallback content when hidden (only used with behavior='hide') */
  fallback?: ReactNode;
}

/**
 * PermissionGate Component
 *
 * Conditionally renders or disables children based on user permissions.
 */
export function PermissionGate({
  children,
  requires,
  behavior = "hide",
  tooltip,
  fallback = null,
}: PermissionGateProps) {
  const { hasAllPermissions, getDenialMessage } = usePermissions();

  const permissions = Array.isArray(requires) ? requires : [requires];
  const hasAccess = hasAllPermissions(permissions);

  // If user has permission, render children normally
  if (hasAccess) {
    return <>{children}</>;
  }

  // HIDE behavior: remove from DOM entirely
  if (behavior === "hide") {
    return <>{fallback}</>;
  }

  // DISABLE behavior: render disabled with tooltip
  const denialMessage = tooltip || getDenialMessage(permissions[0]);

  // Clone child element with disabled props
  if (isValidElement(children)) {
    const childElement = children as ReactElement<{
      disabled?: boolean;
      "aria-disabled"?: boolean;
      className?: string;
    }>;

    const disabledChild = cloneElement(childElement, {
      disabled: true,
      "aria-disabled": true,
      className:
        `${childElement.props.className || ""} opacity-50 cursor-not-allowed`.trim(),
    });

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className="inline-block"
            tabIndex={0}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              // Prevent keyboard activation (Enter/Space)
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
              }
            }}
          >
            <div style={{ pointerEvents: "none" }}>{disabledChild}</div>
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p>{denialMessage}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Fallback for non-element children - treat as hidden for safety
  if (import.meta.env.DEV) {
    console.warn(
      'PermissionGate: behavior="disable" requires a single React element as children',
    );
  }
  return null;
}

/**
 * Convenience component for admin-only content (hidden)
 */
export function AdminOnly({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return (
    <PermissionGate requires="admin_panel" behavior="hide" fallback={fallback}>
      {children}
    </PermissionGate>
  );
}

/**
 * Convenience component for export permission (disabled with tooltip)
 */
export function CanExport({
  children,
  tooltip,
  behavior = "disable",
}: {
  children: ReactNode;
  tooltip?: string;
  behavior?: GateBehavior;
}) {
  return (
    <PermissionGate requires="export" behavior={behavior} tooltip={tooltip}>
      {children}
    </PermissionGate>
  );
}

/**
 * Convenience component for delete permission (hidden by default)
 */
export function CanDelete({
  children,
  fallback,
  behavior = "hide",
}: {
  children: ReactNode;
  fallback?: ReactNode;
  behavior?: GateBehavior;
}) {
  return (
    <PermissionGate requires="delete" behavior={behavior} fallback={fallback}>
      {children}
    </PermissionGate>
  );
}

/**
 * Convenience component for clear permission (hidden by default)
 * Used for "Clear All Data" actions
 */
export function CanClear({
  children,
  fallback,
  behavior = "hide",
}: {
  children: ReactNode;
  fallback?: ReactNode;
  behavior?: GateBehavior;
}) {
  return (
    <PermissionGate requires="clear" behavior={behavior} fallback={fallback}>
      {children}
    </PermissionGate>
  );
}
