import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
}

const statusStyles: Record<string, string> = {
  completed: "bg-success/10 text-success",
  passed: "bg-success/10 text-success",
  failed: "bg-destructive/10 text-destructive",
  running: "bg-info/10 text-info animate-pulse",
  pending: "bg-info/10 text-info",
  skipped: "bg-amber-900/20 text-amber-400",
};

const DEFAULT_STYLE = "bg-muted text-muted-foreground";

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  const style = statusStyles[normalized] ?? DEFAULT_STYLE;

  return (
    <span
      className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", style)}
    >
      {status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
    </span>
  );
}
