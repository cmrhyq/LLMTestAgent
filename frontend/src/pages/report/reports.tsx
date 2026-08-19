import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Download, Eye } from "lucide-react";

import { useReports, downloadReport } from "@/hooks/use-reports.ts";
import { DataTable } from "@/components/shared/data-table.tsx";
import type { Column } from "@/components/shared/data-table.tsx";
import type { Report } from "@/lib/types.ts";
import { formatFileSize } from "@/lib/format";

type ReportRow = Report & Record<string, unknown>;

const columns: Column<ReportRow>[] = [
  {
    key: "test_run_name",
    header: "测试运行",
    render: (val) => <span className="font-medium">{(val as string) || "—"}</span>,
  },
  {
    key: "format",
    header: "格式",
    render: (val) => (
      <span className="inline-flex items-center rounded-md bg-info/10 px-2 py-0.5 text-xs font-medium uppercase text-info">
        {val as string}
      </span>
    ),
  },
  {
    key: "file_size",
    header: "大小",
    render: (val) => (
      <span className="tabular-nums text-muted-foreground">{formatFileSize(val as number)}</span>
    ),
  },
  {
    key: "generated_at",
    header: "生成时间",
    render: (val) => <span className="text-muted-foreground">{val as string}</span>,
  },
];

export default function ReportsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading } = useReports({ page, page_size: pageSize });

  const rows: ReportRow[] = (data?.items ?? []) as ReportRow[];

  const actionsColumn: Column<ReportRow> = {
    key: "_actions",
    header: "操作",
    render: (_, row) => (
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate(`/reports/${row.id}`)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
        >
          <Eye className="h-3.5 w-3.5" />
          查看
        </button>
        <button
          type="button"
          onClick={() => downloadReport(row.id)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
        >
          <Download className="h-3.5 w-3.5" />
          下载
        </button>
      </div>
    ),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-accent" />
        <h1 className="text-2xl font-bold tracking-tight text-foreground">测试报告</h1>
      </div>

      <DataTable
        columns={[...columns, actionsColumn]}
        data={rows}
        loading={isLoading}
        emptyText="暂无生成的报告"
        pagination={
          data
            ? {
                page,
                pageSize,
                total: data.total,
                onChange: setPage,
              }
            : undefined
        }
      />
    </div>
  );
}
