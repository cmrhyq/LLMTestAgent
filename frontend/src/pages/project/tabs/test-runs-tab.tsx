import { DataTable } from "@/components/shared/data-table.tsx";
import { buildTestRunColumns } from "../columns";
import type { TestRun } from "@/lib/types.ts";

export interface TestRunsTabProps {
  data: TestRun[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  onPageChange(page: number): void;
}

export function TestRunsTab({ data, total, loading, page, pageSize, onPageChange }: TestRunsTabProps) {
  return (
    <DataTable
      columns={buildTestRunColumns()}
      data={data}
      loading={loading}
      emptyText="该项目暂无测试运行。"
      pagination={{
        page,
        pageSize,
        total,
        onChange: onPageChange,
      }}
    />
  );
}
