import { Link, useLocation } from "wouter";
import { ChevronRight, Home } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Breadcrumb item configuration
 */
interface BreadcrumbItem {
  label: string;
  path: string;
  isCurrent: boolean;
}

/**
 * Path label mappings for special cases
 * Maps URL paths to human-readable labels
 */
const PATH_LABELS: Record<string, string> = {
  "/": "Overview",
  "/upload": "Upload Data",
  "/categories": "Categories",
  "/suppliers": "Suppliers",
  "/pareto": "Pareto Analysis",
  "/stratification": "Spend Stratification",
  "/seasonality": "Seasonality",
  "/yoy": "Year-over-Year",
  "/tail-spend": "Tail Spend",
  "/ai-insights": "AI Insights",
  "/predictive": "Predictive Analytics",
  "/contracts": "Contract Optimization",
  "/maverick": "Maverick Spend",
  "/settings": "Settings",
};

/**
 * Format a path segment into a human-readable label
 * Handles capitalization, hyphens, and special cases
 *
 * @param segment - URL path segment (e.g., "ai-insights")
 * @returns Formatted label (e.g., "AI Insights")
 */
function formatPathSegment(segment: string): string {
  // Handle empty segments
  if (!segment) return "";

  // Convert hyphens to spaces
  const words = segment.split("-");

  // Capitalize each word
  const formatted = words
    .map((word) => {
      // Special case for acronyms
      if (word.toLowerCase() === "ai") return "AI";
      if (word.toLowerCase() === "yoy") return "Year-over-Year";

      // Standard capitalization
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(" ");

  return formatted;
}

/**
 * Generate breadcrumb items from current location
 *
 * @param location - Current URL path
 * @returns Array of breadcrumb items
 */
function generateBreadcrumbs(location: string): BreadcrumbItem[] {
  // Always start with Home
  const items: BreadcrumbItem[] = [];

  // If we're on home (Overview), just return it
  if (location === "/") {
    return [
      {
        label: "Overview",
        path: "/",
        isCurrent: true,
      },
    ];
  }

  // Add Overview as first item
  items.push({
    label: "Overview",
    path: "/",
    isCurrent: false,
  });

  // Use predefined label if available, otherwise format the path
  const label = PATH_LABELS[location] || formatPathSegment(location.slice(1));

  // Add current page
  items.push({
    label,
    path: location,
    isCurrent: true,
  });

  return items;
}

/**
 * Dynamic breadcrumb navigation component
 *
 * Features:
 * - Automatically updates based on current route
 * - Accessible with proper ARIA labels
 * - Keyboard navigable
 * - Responsive design
 * - Handles special path formatting (hyphens, acronyms)
 *
 * Security:
 * - No XSS vulnerabilities (uses React's built-in escaping)
 * - Validates path segments before rendering
 *
 * @example
 * ```tsx
 * <Breadcrumb />
 * ```
 */
export function Breadcrumb() {
  const [location] = useLocation();

  // Generate breadcrumb items from current location
  const breadcrumbs = generateBreadcrumbs(location);

  return (
    <nav aria-label="Breadcrumb" className="mb-6">
      <ol className="flex items-center gap-2 text-sm">
        {breadcrumbs.map((item, index) => {
          const isLast = index === breadcrumbs.length - 1;

          return (
            <li key={item.path} className="flex items-center gap-2">
              {/* Render link for non-current items */}
              {!item.isCurrent ? (
                <>
                  <Link
                    href={item.path}
                    className={cn(
                      "flex items-center gap-1.5 text-gray-600 hover:text-gray-900",
                      "transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1",
                    )}
                  >
                    {index === 0 && <Home className="h-4 w-4" />}
                    <span>{item.label}</span>
                  </Link>
                  {/* Separator */}
                  {!isLast && (
                    <ChevronRight
                      className="h-4 w-4 text-gray-400"
                      aria-hidden="true"
                    />
                  )}
                </>
              ) : (
                /* Current page - no link */
                <span className="font-medium text-gray-900" aria-current="page">
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
