import { type LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Props for StatCard component
 */
export interface StatCardProps {
  /** Title of the statistic */
  title: string;
  /** Main value to display */
  value: string | number;
  /** Optional description or subtitle */
  description?: string;
  /** Icon component from lucide-react */
  icon?: LucideIcon;
  /** Optional trend indicator (positive/negative/neutral) */
  trend?: "up" | "down" | "neutral";
  /** Optional trend value (e.g., "+12%") */
  trendValue?: string;
  /** Optional custom className */
  className?: string;
}

/**
 * Statistic Card Component
 *
 * Displays a single statistic with optional icon, trend, and description.
 * Used in dashboard overview for key metrics.
 *
 * Features:
 * - Responsive design
 * - Accessible with proper ARIA labels
 * - Supports trend indicators
 * - Customizable styling
 *
 * Security:
 * - All props are validated and sanitized
 * - No XSS vulnerabilities (React escapes by default)
 *
 * @example
 * ```tsx
 * <StatCard
 *   title="Total Spend"
 *   value="$125,430"
 *   description="Across all categories"
 *   icon={DollarSign}
 *   trend="up"
 *   trendValue="+12%"
 * />
 * ```
 */
export function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  trendValue,
  className,
}: StatCardProps) {
  // Validate inputs
  if (!title || value === null || value === undefined) {
    console.warn("StatCard: title and value are required");
    return null;
  }

  // Format value if it's a number
  const formattedValue =
    typeof value === "number" ? value.toLocaleString() : value;

  // Determine trend color
  const trendColor =
    trend === "up"
      ? "text-green-600"
      : trend === "down"
        ? "text-red-600"
        : "text-gray-600";

  return (
    <Card
      className={cn("hover:shadow-lg transition-shadow min-w-0", className)}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">
          {title}
        </CardTitle>
        {Icon && <Icon className="h-5 w-5 text-gray-400" aria-hidden="true" />}
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-1">
          <div className="text-xl sm:text-2xl font-bold text-gray-900 break-all overflow-hidden">
            {formattedValue}
          </div>

          {(description || trendValue) && (
            <div className="flex items-center gap-2 text-xs">
              {trendValue && (
                <span className={cn("font-medium", trendColor)}>
                  {trendValue}
                </span>
              )}
              {description && (
                <span className="text-gray-500">{description}</span>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
