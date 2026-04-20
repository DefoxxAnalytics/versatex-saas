import { PlaceholderPage } from "@/components/PlaceholderPage";
import { Users } from "lucide-react";

export default function SuppliersPage() {
  return (
    <PlaceholderPage
      title="Suppliers Analysis"
      description="Track supplier performance and optimize vendor relationships"
      icon={<Users className="h-8 w-8 text-purple-600" />}
    />
  );
}
