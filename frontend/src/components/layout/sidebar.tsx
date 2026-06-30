import { NavLink } from "react-router-dom";
import { LayoutDashboard, Play, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

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
            ? "border-l-2 border-accent bg-secondary font-medium text-foreground"
            : "border-l-2 border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground"
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
}

export function Sidebar({ collapsed }: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-border bg-card overflow-hidden transition-all duration-200",
        collapsed ? "w-0 border-r-0" : "w-[200px]"
      )}
    >
      <nav className="flex flex-1 flex-col gap-1 p-3 min-w-[200px]">
        <NavItem to="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />} label="Dashboard" />

        <div className="mt-4 mb-2 px-3">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Workflows
          </span>
        </div>

        {/*<NavItem*/}
        {/*  to="/workflows/parse"*/}
        {/*  icon={<FileUp className="h-4 w-4" />}*/}
        {/*  label="Parse Document"*/}
        {/*/>*/}
        <NavItem to="/workflows/run" icon={<Play className="h-4 w-4" />} label="New Test" />

        <div className="mt-4 mb-2 px-3">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Results
          </span>
        </div>

        <NavItem to="/reports" icon={<FileText className="h-4 w-4" />} label="Reports" />
      </nav>
    </aside>
  );
}
