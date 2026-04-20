/**
 * SkeletonCard Component
 *
 * A skeleton placeholder for stat cards that displays during loading.
 * Matches the visual structure of StatCard for seamless loading transitions.
 */

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonCardProps {
  /** Whether to show the icon placeholder */
  showIcon?: boolean;
}

export function SkeletonCard({ showIcon = true }: SkeletonCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        {showIcon && <Skeleton className="h-4 w-4 rounded" />}
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}
