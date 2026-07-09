import { Link } from "react-router-dom";
import { LayoutDashboard, Play, FileText, MessageSquare, PanelLeftClose } from "lucide-react";
import { cn } from "@/lib/utils";
import { NavLink } from "react-router";
import { SpacesSection } from "@/components/layout/spaces-section";

const APP_VERSION = "v0.0.1";
const SIDEBAR_WIDTH = 250;

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors no-underline",
          isActive
            ? "border-l-2 border-accent bg-blue-50 font-medium text-foreground"
            : "border-l-2 border-transparent text-muted-foreground hover:bg-blue-100 hover:text-foreground"
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className="flex h-full min-h-0 shrink-0 flex-col overflow-hidden border-r border-border bg-sidebar transition-[width] duration-300 ease-in-out"
      style={{ width: collapsed ? 0 : SIDEBAR_WIDTH }}
    >
      <div
        className={cn(
          "flex h-full min-h-0 min-w-[250px] flex-col overflow-hidden transition-opacity duration-200",
          collapsed ? "pointer-events-none opacity-0" : "opacity-100"
        )}
      >
        <div className="flex items-start justify-between gap-2 px-4 pb-3 pt-4">
          <Link to="/dashboard" className="flex min-w-0 items-start gap-2.5 no-underline">
            <img src="/favicon.svg" alt="Logo" className="mt-0.5 h-6 w-6 shrink-0" />
            <div className="min-w-0">
              <span className="block text-sm font-medium text-foreground">LLMTestAgent</span>
              <span className="block text-[10px] text-muted-foreground">{APP_VERSION}</span>
            </div>
          </Link>
          <button
            type="button"
            onClick={onToggle}
            aria-label="隐藏侧边栏"
            className="shrink-0 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex shrink-0 flex-col gap-0.5 px-3 pb-4">
          <NavItem to="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />} label="仪表盘" />

          <div className="mb-1 mt-5 px-2.5">
            <span className="text-[11px] font-medium text-muted-foreground">工作流</span>
          </div>

          <NavItem to="/workflows/run" icon={<Play className="h-4 w-4" />} label="新建测试" />
          <NavItem
            to="/workflows/chat"
            icon={<MessageSquare className="h-4 w-4" />}
            label="安全对话"
          />

          <div className="mb-1 mt-5 px-2.5">
            <span className="text-[11px] font-medium text-muted-foreground">结果</span>
          </div>

          <NavItem to="/reports" icon={<FileText className="h-4 w-4" />} label="报告" />
        </nav>

        <div className="mt-auto flex min-h-0 flex-1 flex-col overflow-hidden border-t border-border">
          <SpacesSection />
        </div>
      </div>
    </aside>
  );
}
