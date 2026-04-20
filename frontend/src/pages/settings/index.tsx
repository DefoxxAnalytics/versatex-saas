import { PlaceholderPage } from "@/components/PlaceholderPage";
import { Settings as SettingsIcon } from "lucide-react";

export default function SettingsPage() {
  return (
    <PlaceholderPage
      title="Settings"
      description="Configure your dashboard preferences and options"
      icon={<SettingsIcon className="h-8 w-8 text-gray-600" />}
    />
  );
}
