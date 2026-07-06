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
  skipped: "bg-amber-100 text-amber-700",
};

const DEFAULT_STYLE = "bg-muted text-muted-foreground";

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  passed: "已通过",
  failed: "已失败",
  running: "运行中",
  pending: "等待中",
  skipped: "已跳过",
  error: "错误",
  active: "已启用",
  inactive: "未启用",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  const style = statusStyles[normalized] ?? DEFAULT_STYLE;
  const label =
    STATUS_LABELS[normalized] ?? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();

  return (
    <span
      className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", style)}
    >
      {label}
    </span>
  );
}
