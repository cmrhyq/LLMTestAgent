import { useState } from "react";
import { Outlet } from "react-router-dom";
import { HeaderNav } from "./header-nav";
import { Sidebar } from "./sidebar";
import { ErrorBoundary } from "@/components/shared/error-boundary";

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <HeaderNav onToggleSidebar={() => setSidebarCollapsed((v) => !v)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar collapsed={sidebarCollapsed} />
        <main className="flex-1 overflow-y-auto p-6 rounded-xl">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
