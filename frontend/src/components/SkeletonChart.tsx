/**
 * SkeletonChart Component
 *
 * A skeleton placeholder for chart components that displays during loading.
 * Shows animated bar placeholders to indicate chart loading state.
 */

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SkeletonChartProps {
  /** Height of the chart area in pixels */
  height?: number;
  /** Additional CSS classes */
  className?: string;
  /** Chart type to determine skeleton shape */
  type?: "bar" | "line" | "pie" | "area";
  /** Whether to show card wrapper */
  showCard?: boolean;
}

export function SkeletonChart({
  height = 300,
  className,
  type = "bar",
  showCard = true,
}: SkeletonChartProps) {
  const chartContent = (
    <div className={cn("w-full", className)} style={{ height }}>
      {type === "bar" && (
        <div className="flex items-end justify-around gap-2 h-full p-4">
          {[40, 70, 55, 90, 65, 80, 45, 75, 60, 85].map((h, i) => (
            <Skeleton
              key={i}
              className="flex-1 max-w-[40px] rounded-t-md"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      )}
      {type === "line" && (
        <div className="relative h-full p-4">
          {/* Grid lines */}
          <div className="absolute inset-4 flex flex-col justify-between">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-px w-full opacity-30" />
            ))}
          </div>
          {/* Animated line path representation */}
          <div className="absolute inset-4 flex items-end">
            <svg className="w-full h-full" preserveAspectRatio="none">
              <path
                d="M 0 80 Q 50 60 100 70 T 200 50 T 300 65 T 400 40 T 500 55"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                className="text-muted-foreground/20 animate-pulse"
              />
            </svg>
          </div>
        </div>
      )}
      {type === "pie" && (
        <div className="flex items-center justify-center h-full p-4">
          <Skeleton className="w-48 h-48 rounded-full" />
        </div>
      )}
      {type === "area" && (
        <div className="relative h-full p-4">
          {/* Grid lines */}
          <div className="absolute inset-4 flex flex-col justify-between">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-px w-full opacity-30" />
            ))}
          </div>
          {/* Animated area representation */}
          <div className="absolute inset-4 flex items-end">
            <Skeleton className="w-full h-3/4 rounded-t-lg opacity-50" />
          </div>
        </div>
      )}
    </div>
  );

  if (!showCard) {
    return chartContent;
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64 mt-1" />
      </CardHeader>
      <CardContent>{chartContent}</CardContent>
    </Card>
  );
}

/**
 * SkeletonTable Component
 *
 * A skeleton placeholder for table components.
 */
interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  showCard?: boolean;
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  showCard = true,
}: SkeletonTableProps) {
  const tableContent = (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex gap-4 pb-2 border-b">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} className="h-4 flex-1" />
        ))}
      </div>
      {/* Data rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex gap-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={`cell-${rowIndex}-${colIndex}`}
              className="h-4 flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  );

  if (!showCard) {
    return tableContent;
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>{tableContent}</CardContent>
    </Card>
  );
}
