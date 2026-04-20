import { PlaceholderPage } from "@/components/PlaceholderPage";
import { Calendar } from "lucide-react";

export default function SeasonalityPage() {
  return (
    <PlaceholderPage
      title="Seasonality Intelligence"
      description="Discover time-based spending patterns and seasonal trends"
      icon={<Calendar className="h-8 w-8 text-orange-600" />}
    />
  );
}
