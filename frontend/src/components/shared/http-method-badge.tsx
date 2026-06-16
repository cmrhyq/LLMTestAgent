import { cn } from "@/lib/utils";

interface HttpMethodBadgeProps {
  method: string;
}

const methodStyles: Record<string, string> = {
  GET: "bg-emerald-900/20 text-emerald-400",
  POST: "bg-blue-900/20 text-blue-400",
  PUT: "bg-amber-900/20 text-amber-400",
  DELETE: "bg-red-900/20 text-red-400",
  PATCH: "bg-sky-900/20 text-sky-400",
};

const DEFAULT_STYLE = "bg-muted text-muted-foreground";

export function HttpMethodBadge({ method }: HttpMethodBadgeProps) {
  const upper = method.toUpperCase();
  const style = methodStyles[upper] ?? DEFAULT_STYLE;

  return (
    <span
      className={cn(
        "inline-flex w-16 items-center justify-center rounded font-mono text-xs font-semibold uppercase",
        style
      )}
    >
      {upper}
    </span>
  );
}
