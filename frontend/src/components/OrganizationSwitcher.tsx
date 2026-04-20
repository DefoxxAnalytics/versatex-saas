/**
 * Organization Switcher component for multi-org users
 *
 * Allows superusers and multi-org users to switch between organizations.
 * Displays role badges for multi-org users to show their role in each org.
 * Single-org users will not see this component.
 */
import {
  Building2,
  ChevronDown,
  Check,
  FlaskConical,
  RotateCcw,
  Shield,
  Star,
} from "lucide-react";
import { useOrganization } from "@/contexts/OrganizationContext";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ColorScheme } from "@/hooks/useSettings";
import type { UserRole } from "@/lib/api";

interface OrganizationSwitcherProps {
  colorScheme?: ColorScheme;
}

// Role badge colors
const roleColors: Record<UserRole, string> = {
  admin: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  manager: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  viewer: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

export function OrganizationSwitcher({
  colorScheme = "navy",
}: OrganizationSwitcherProps) {
  const { isSuperAdmin } = useAuth();
  const {
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
  } = useOrganization();

  // Don't render if user can't switch
  if (!canSwitch || isLoading) {
    return null;
  }

  // Get button styles based on color scheme
  const buttonStyles =
    colorScheme === "navy"
      ? "text-white hover:bg-blue-700 border-blue-700"
      : "text-gray-700 hover:bg-gray-100 border-gray-200";

  const activeStyles = isViewingOtherOrg
    ? colorScheme === "navy"
      ? "bg-amber-500/20 border-amber-400/50 text-amber-100"
      : "bg-amber-50 border-amber-200 text-amber-800"
    : "";

  const demoTriggerStyles = activeOrganization?.is_demo
    ? "ring-1 ring-amber-400/60 ring-offset-0"
    : "";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "flex items-center gap-2 h-9 px-3 transition-colors",
            buttonStyles,
            activeStyles,
            demoTriggerStyles,
          )}
        >
          <Building2 className="h-4 w-4" />
          <span className="max-w-[120px] truncate hidden sm:inline">
            {activeOrganization?.name || "Select Org"}
          </span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          Switch Organization
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Reset to default option */}
        {isViewingOtherOrg && userOrganization && (
          <>
            <DropdownMenuItem
              onClick={resetToDefault}
              className="flex items-center gap-2 text-blue-600 dark:text-blue-400"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reset to My Organization</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}

        {/* Organization list */}
        <div className="max-h-64 overflow-y-auto">
          {organizations.map((org) => {
            const isActive = activeOrganization?.id === org.id;
            const isUserOrg = userOrganization?.id === org.id;
            const orgRole = getRoleInOrg(org.id);

            return (
              <DropdownMenuItem
                key={org.id}
                onClick={() => switchOrganization(org.id)}
                className={cn(
                  "flex items-center justify-between gap-2",
                  isActive && "bg-accent",
                )}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Building2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="truncate">{org.name}</span>
                  {isUserOrg && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Star className="h-3 w-3" />
                      Primary
                    </span>
                  )}
                  {org.is_demo && (
                    <Badge
                      variant="secondary"
                      aria-label="Synthetic demo data"
                      className="text-xs px-1.5 py-0 bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 flex items-center gap-1"
                    >
                      <FlaskConical
                        className="h-3 w-3"
                        aria-hidden="true"
                      />
                      Demo
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {/* Show role badge for multi-org users (not superadmins) */}
                  {isMultiOrgUser && !isSuperAdmin && orgRole && (
                    <Badge
                      variant="secondary"
                      className={cn("text-xs px-1.5 py-0", roleColors[orgRole])}
                    >
                      {orgRole}
                    </Badge>
                  )}
                  {/* Superadmin badge */}
                  {isSuperAdmin && (
                    <Badge
                      variant="secondary"
                      className="text-xs px-1.5 py-0 bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                    >
                      <Shield className="h-3 w-3 mr-0.5" />
                      super
                    </Badge>
                  )}
                  {isActive && <Check className="h-4 w-4 text-primary" />}
                </div>
              </DropdownMenuItem>
            );
          })}
        </div>

        {/* Show current role info for multi-org users */}
        {isMultiOrgUser && !isSuperAdmin && activeRole && (
          <>
            <DropdownMenuSeparator />
            <div className="px-2 py-1.5 text-xs text-muted-foreground">
              Current role:{" "}
              <span className="font-medium capitalize">{activeRole}</span>
            </div>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
