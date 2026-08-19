import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string | number;
}

const statusStyles: Record<string, string> = {
  completed: "bg-success/10 text-success",
  passed: "bg-success/10 text-success",
  failed: "bg-destructive/10 text-destructive",
  running: "bg-info/10 text-info animate-pulse",
  pending: "bg-info/10 text-info",
  skipped: "bg-warning/10 text-warning",
  active: "bg-success/10 text-success",
  inactive: "bg-muted text-muted-foreground",
  deleted: "bg-muted text-muted-foreground",
  deprecated: "bg-warning/10 text-warning",
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
  deleted: "已删除",
  deprecated: "已废弃",
};

/** 数值状态（DataStatus：1 启用 / 2 禁用 / 3 删除 / 4 废弃）→ 语义名。 */
const NUMERIC_STATUS: Record<number, string> = {
  1: "active",
  2: "inactive",
  3: "deleted",
  4: "deprecated",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = (typeof status === "number" ? NUMERIC_STATUS[status] ?? "" : status).toLowerCase();
  const style = statusStyles[normalized] ?? DEFAULT_STYLE;
  const label =
    STATUS_LABELS[normalized] ?? (normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : String(status));

  return (
    <span
      className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", style)}
    >
      {label}
    </span>
  );
}
