import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export interface Column<T> {
  key: string;
  header: string;
  render?: (value: unknown, row: T) => ReactNode;
  className?: string;
}

interface PaginationConfig {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

interface DataTableProps<T extends object> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyText?: string;
  pagination?: PaginationConfig;
}

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc !== null && acc !== undefined && typeof acc === "object") {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function DataTable<T extends object>({
  columns,
  data,
  loading = false,
  emptyText = "No data available",
  pagination,
}: DataTableProps<T>) {
  const totalPages = pagination
    ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize))
    : 1;

  const SKELETON_ROWS = 5;

  return (
    <div className="w-full overflow-hidden rounded-md border border-border">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-card">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-4 py-3 text-left font-medium text-muted-foreground",
                    col.className
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading &&
              Array.from({ length: SKELETON_ROWS }).map((_, rowIdx) => (
                <tr key={`skeleton-${rowIdx.toString()}`} className="border-b border-border">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      <Skeleton className="h-4 w-3/4" />
                    </td>
                  ))}
                </tr>
              ))}

            {!loading && data.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-muted-foreground"
                >
                  {emptyText}
                </td>
              </tr>
            )}

            {!loading &&
              data.map((row, rowIdx) => (
                <tr
                  key={rowIdx.toString()}
                  className="border-b border-border transition-colors hover:bg-card last:border-b-0"
                >
                  {columns.map((col) => {
                    const value = getNestedValue(row, col.key);
                    return (
                      <td key={col.key} className={cn("px-4 py-3", col.className)}>
                        {col.render ? col.render(value, row) : String(value ?? "")}
                      </td>
                    );
                  })}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between border-t px-4 py-3">
          <span className="text-sm text-muted-foreground">
            Page {pagination.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={pagination.page <= 1}
              onClick={() => pagination.onChange(pagination.page - 1)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                pagination.page <= 1 ? "cursor-not-allowed opacity-50" : "hover:bg-muted"
              )}
            >
              Previous
            </button>
            <button
              type="button"
              disabled={pagination.page >= totalPages}
              onClick={() => pagination.onChange(pagination.page + 1)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                pagination.page >= totalPages ? "cursor-not-allowed opacity-50" : "hover:bg-muted"
              )}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
