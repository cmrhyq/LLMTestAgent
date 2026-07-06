import { cn } from "@/lib/utils";

interface HttpMethodBadgeProps {
  method: string;
}

const methodStyles: Record<string, string> = {
  GET: "bg-emerald-100 text-emerald-700",
  POST: "bg-blue-100 text-blue-700",
  PUT: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
  PATCH: "bg-sky-100 text-sky-700",
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
