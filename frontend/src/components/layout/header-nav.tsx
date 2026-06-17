import { useState } from "react";
import { Link } from "react-router-dom";
import { PanelLeft, Settings } from "lucide-react";
import { SettingsDialog } from "./settings-dialog";

interface HeaderNavProps {
  onToggleSidebar: () => void;
}

export function HeaderNav({ onToggleSidebar }: HeaderNavProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 h-12 border-b border-border bg-card">
      <div className="flex h-full items-center px-4 gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <PanelLeft className="h-5 w-5" />
        </button>

        <Link to="/dashboard" className="flex items-center gap-2 no-underline">
          <img src="/favicon.svg" alt="Logo" className="h-6 w-6" />
          <span className="text-sm font-semibold text-foreground">LLMTestAgent</span>
        </Link>

        <div className="flex-1" />

        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <Settings className="h-4.5 w-4.5" />
        </button>
      </div>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  );
}
