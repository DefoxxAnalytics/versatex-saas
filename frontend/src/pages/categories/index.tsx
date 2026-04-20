import { PlaceholderPage } from "@/components/PlaceholderPage";
import { FolderTree } from "lucide-react";

export default function CategoriesPage() {
  return (
    <PlaceholderPage
      title="Categories Analysis"
      description="Analyze spending patterns across different procurement categories"
      icon={<FolderTree className="h-8 w-8 text-blue-600" />}
    />
  );
}
