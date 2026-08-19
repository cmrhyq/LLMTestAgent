import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download } from "lucide-react";

import { useReportDetail, downloadReport } from "@/hooks/use-reports.ts";
import { Button } from "@/components/ui/button.tsx";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card.tsx";
import { Skeleton } from "@/components/ui/skeleton.tsx";
import { PassRateBar } from "@/components/shared/pass-rate-bar.tsx";
import { TestResultsTable } from "@/components/report/test-results-table.tsx";
import { ResponseTimeStats } from "@/components/report/response-time-stats.tsx";
import { formatDuration } from "@/lib/format";

export default function ReportViewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reportId = id || "";

  const { data, isLoading, isError } = useReportDetail(reportId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回
        </Button>
        <p className="text-destructive">加载报告详情失败。</p>
      </div>
    );
  }

  const { test_run, test_results } = data;
  const failedResults = test_results.filter((r) => r.status === "failed" || r.status === "error");

  const summaryCards = [
    { label: "总数", value: String(test_run.total_cases), className: "" },
    { label: "已通过", value: String(test_run.passed_cases), className: "text-success" },
    { label: "已失败", value: String(test_run.failed_cases), className: "text-destructive" },
    { label: "已跳过", value: String(test_run.skipped_cases), className: "" },
    { label: "错误", value: String(test_run.error_cases), className: "text-warning" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{test_run.name}</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {test_run.llm_provider} / {test_run.llm_model} &middot; 生成于 {data.generated_at}
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => downloadReport(data.id)}>
          <Download className="mr-2 h-4 w-4" />
          下载 HTML
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {summaryCards.map((c) => (
          <Card key={c.label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{c.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className={`text-2xl font-bold ${c.className}`}>{c.value}</p>
            </CardContent>
          </Card>
        ))}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">通过率</CardTitle>
          </CardHeader>
          <CardContent>
            <PassRateBar passed={test_run.passed_cases} total={test_run.total_cases} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">耗时</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{formatDuration(test_run.total_duration)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Response time stats */}
      <ResponseTimeStats results={test_results} />

      {/* Failed/error cases */}
      {failedResults.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-destructive">
            失败 / 错误用例（{failedResults.length}）
          </h2>
          <TestResultsTable results={failedResults} danger />
        </div>
      )}

      {/* All test results */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">
          全部测试结果（{test_results.length}）
        </h2>
        <TestResultsTable results={test_results} />
      </div>
    </div>
  );
}
