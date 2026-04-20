import { PlaceholderPage } from "@/components/PlaceholderPage";
import { Layers } from "lucide-react";

export default function StratificationPage() {
  return (
    <PlaceholderPage
      title="Spend Stratification"
      description="Segment spending into strategic tiers for better management"
      icon={<Layers className="h-8 w-8 text-indigo-600" />}
    />
  );
}
