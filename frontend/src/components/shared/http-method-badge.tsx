import { cn } from "@/lib/utils";

interface HttpMethodBadgeProps {
  method: string;
}

const methodStyles: Record<string, string> = {
  GET: "bg-success/10 text-success",
  POST: "bg-info/10 text-info",
  PUT: "bg-warning/10 text-warning",
  DELETE: "bg-destructive/10 text-destructive",
  PATCH: "bg-accent/10 text-accent",
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
