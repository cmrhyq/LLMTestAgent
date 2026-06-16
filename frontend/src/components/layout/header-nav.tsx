import { Link } from "react-router-dom";
import { FlaskConical, PanelLeft } from "lucide-react";

interface HeaderNavProps {
  onToggleSidebar: () => void;
}

export function HeaderNav({ onToggleSidebar }: HeaderNavProps) {
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
          <FlaskConical className="h-5 w-5 text-foreground" />
          <span className="text-sm font-semibold text-foreground">LLMTestAgent</span>
        </Link>
      </div>
    </header>
  );
}
