const rtf = new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" });

const UNITS: { unit: Intl.RelativeTimeFormatUnit; ms: number }[] = [
  { unit: "year", ms: 365 * 24 * 60 * 60 * 1000 },
  { unit: "month", ms: 30 * 24 * 60 * 60 * 1000 },
  { unit: "week", ms: 7 * 24 * 60 * 60 * 1000 },
  { unit: "day", ms: 24 * 60 * 60 * 1000 },
  { unit: "hour", ms: 60 * 60 * 1000 },
  { unit: "minute", ms: 60 * 1000 },
  { unit: "second", ms: 1000 },
];

export function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const diffMs = date.getTime() - Date.now();
  const absDiffMs = Math.abs(diffMs);

  for (const { unit, ms } of UNITS) {
    if (absDiffMs >= ms || unit === "second") {
      const value = Math.round(diffMs / ms);
      return rtf.format(value, unit);
    }
  }

  return rtf.format(0, "second");
}
