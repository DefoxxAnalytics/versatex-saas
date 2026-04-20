import { PlaceholderPage } from "@/components/PlaceholderPage";
import { TrendingUp } from "lucide-react";

export default function ParetoPage() {
  return (
    <PlaceholderPage
      title="Pareto Analysis"
      description="Identify the 20% of suppliers driving 80% of spend"
      icon={<TrendingUp className="h-8 w-8 text-green-600" />}
    />
  );
}
