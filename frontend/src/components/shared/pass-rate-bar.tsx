import { cn } from "@/lib/utils";

interface PassRateBarProps {
  passed: number;
  total: number;
}

export function PassRateBar({ passed, total }: PassRateBarProps) {
  if (total === 0) {
    return <span className="text-sm text-muted-foreground">--</span>;
  }

  const percentage = Math.round((passed / total) * 100);

  const barColor =
    percentage >= 80 ? "bg-emerald-500" : percentage >= 50 ? "bg-amber-500" : "bg-red-500";

  const textColor =
    percentage >= 80 ? "text-emerald-400" : percentage >= 50 ? "text-amber-400" : "text-red-400";

  return (
    <div className="flex items-center gap-2">
      <span className={cn("text-sm font-medium tabular-nums", textColor)}>{percentage}%</span>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
