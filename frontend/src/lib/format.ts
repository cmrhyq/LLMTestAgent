import { formatRelativeTime } from "@/lib/format-relative-time";

export { formatRelativeTime };

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatJson(raw: string | null | undefined): string {
  if (!raw) return "";
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return date.toLocaleDateString();
}

export function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "--";
  return `${seconds.toFixed(1)}s`;
}

export function formatResponseTime(ms: number): string {
  return `${ms.toFixed(1)} ms`;
}
