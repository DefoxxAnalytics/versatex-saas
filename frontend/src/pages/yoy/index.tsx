import { PlaceholderPage } from "@/components/PlaceholderPage";
import { BarChart3 } from "lucide-react";

export default function YoYPage() {
  return (
    <PlaceholderPage
      title="Year-over-Year Comparison"
      description="Compare spending trends across different time periods"
      icon={<BarChart3 className="h-8 w-8 text-cyan-600" />}
    />
  );
}
