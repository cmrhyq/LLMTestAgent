import { Wrench } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>

      <Card>
        <CardContent className="py-12">
          <EmptyState icon={<Wrench />} title="Settings" description="Settings page coming soon" />
        </CardContent>
      </Card>
    </div>
  );
}
