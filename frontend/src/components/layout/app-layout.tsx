import { useState } from "react";
import { Outlet } from "react-router-dom";
import { PanelRightClose } from "lucide-react";
import { Sidebar } from "./sidebar";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn } from "@/lib/utils";

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(true)} />
      <main className="relative flex-1 overflow-y-auto bg-background p-6">
        {sidebarCollapsed && (
          <button
            type="button"
            onClick={() => setSidebarCollapsed(false)}
            aria-label="展开侧边栏"
            className={cn(
              "fixed left-2 top-2 z-50 flex h-9 w-9 items-center justify-center rounded-full",
              "border border-border bg-background text-muted-foreground shadow-elevated transition-colors",
              "hover:bg-muted hover:text-foreground",
              "animate-in fade-in-0 zoom-in-95 duration-200"
            )}
          >
            <PanelRightClose className="h-5 w-5" />
          </button>
        )}
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
