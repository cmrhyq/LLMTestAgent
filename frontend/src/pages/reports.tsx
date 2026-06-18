import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Download, Eye } from "lucide-react";

import { useReports, downloadReport } from "@/hooks/use-reports";
import { DataTable } from "@/components/shared/data-table";
import type { Column } from "@/components/shared/data-table";
import type { Report } from "@/lib/types";

type ReportRow = Report & Record<string, unknown>;

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const columns: Column<ReportRow>[] = [
  {
    key: "test_run_name",
    header: "Test Run",
    render: (val) => <span className="font-medium">{(val as string) || "—"}</span>,
  },
  {
    key: "format",
    header: "Format",
    render: (val) => (
      <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs font-medium uppercase">
        {val as string}
      </span>
    ),
  },
  {
    key: "file_size",
    header: "Size",
    render: (val) => (
      <span className="tabular-nums text-muted-foreground">{formatFileSize(val as number)}</span>
    ),
  },
  {
    key: "generated_at",
    header: "Generated At",
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
    header: "Actions",
    render: (_, row) => (
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate(`/reports/${row.id}`)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted"
        >
          <Eye className="h-3.5 w-3.5" />
          View
        </button>
        <button
          type="button"
          onClick={() => downloadReport(row.id)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted"
        >
          <Download className="h-3.5 w-3.5" />
          Download
        </button>
      </div>
    ),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-muted-foreground" />
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Test Reports</h1>
      </div>

      <DataTable
        columns={[...columns, actionsColumn]}
        data={rows}
        loading={isLoading}
        emptyText="No reports generated yet"
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
