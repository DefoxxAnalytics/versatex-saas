import { ReactNode } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Construction } from "lucide-react";

/**
 * Reusable placeholder component for pages under development
 *
 * @param title - Page title
 * @param description - Page description
 * @param icon - Optional icon component
 * @param children - Optional additional content
 */
interface PlaceholderPageProps {
  title: string;
  description: string;
  icon?: ReactNode;
  children?: ReactNode;
}

export function PlaceholderPage({
  title,
  description,
  icon,
  children,
}: PlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          {icon}
          <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        </div>
        <p className="text-gray-600">{description}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Construction className="h-5 w-5 text-yellow-600" />
            Coming Soon
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            This feature is currently under development. Check back soon for
            powerful analytics and insights!
          </p>
          {children}
        </CardContent>
      </Card>
    </div>
  );
}
