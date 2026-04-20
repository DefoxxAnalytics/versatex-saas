/**
 * Organization Badge component
 *
 * Displays an amber badge when a superuser is viewing another organization's data.
 * Provides clear visual feedback that the user is not viewing their own data.
 */
import { Eye } from "lucide-react";
import { useOrganization } from "@/contexts/OrganizationContext";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ColorScheme } from "@/hooks/useSettings";

interface OrganizationBadgeProps {
  colorScheme?: ColorScheme;
  className?: string;
}

export function OrganizationBadge({
  colorScheme = "navy",
  className,
}: OrganizationBadgeProps) {
  const { activeOrganization, isViewingOtherOrg, isLoading } =
    useOrganization();

  // Don't render if not viewing another org
  if (!isViewingOtherOrg || isLoading || !activeOrganization) {
    return null;
  }

  // Badge styles based on color scheme
  const badgeStyles =
    colorScheme === "navy"
      ? "bg-amber-500/20 text-amber-100 border-amber-400/50 hover:bg-amber-500/30"
      : "bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100";

  return (
    <Badge
      variant="outline"
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 font-normal transition-colors",
        badgeStyles,
        className,
      )}
    >
      <Eye className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">Viewing:</span>
      <span className="font-medium max-w-[100px] truncate">
        {activeOrganization.name}
      </span>
    </Badge>
  );
}
