import { PlaceholderPage } from "@/components/PlaceholderPage";
import { Target } from "lucide-react";

export default function TailSpendPage() {
  return (
    <PlaceholderPage
      title="Tail Spend Analysis"
      description="Analyze and optimize long-tail spending patterns"
      icon={<Target className="h-8 w-8 text-red-600" />}
    />
  );
}
