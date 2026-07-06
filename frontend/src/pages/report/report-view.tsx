import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, ChevronDown, ChevronRight } from "lucide-react";

import { useReportDetail, downloadReport } from "@/hooks/use-reports.ts";
import { Button } from "@/components/ui/button.tsx";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card.tsx";
import { Skeleton } from "@/components/ui/skeleton.tsx";
import { StatusBadge } from "@/components/shared/status-badge.tsx";
import { HttpMethodBadge } from "@/components/shared/http-method-badge.tsx";
import { PassRateBar } from "@/components/shared/pass-rate-bar.tsx";
import type { TestResultDetail } from "@/lib/types.ts";
import { cn } from "@/lib/utils.ts";

function formatJson(raw: string | null): string {
  if (!raw) return "";
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function ResponseTimeStats({ results }: { results: TestResultDetail[] }) {
  const times = results.map((r) => r.response_time).filter((t) => t > 0);

  if (times.length === 0) return null;

  const avg = times.reduce((a, b) => a + b, 0) / times.length;
  const min = Math.min(...times);
  const max = Math.max(...times);
  const sorted = [...times].sort((a, b) => a - b);
  const p95Idx = Math.min(Math.floor(sorted.length * 0.95), sorted.length - 1);
  const p95 = sorted[p95Idx];

  const stats = [
    { label: "平均", value: avg },
    { label: "最小", value: min },
    { label: "最大", value: max },
    { label: "P95", value: p95 },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {s.label}响应
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-bold tabular-nums">
              {s.value.toFixed(1)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">ms</span>
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ExpandableRow({ result }: { result: TestResultDetail }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-border transition-colors hover:bg-card cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3">
          <span className="inline-flex items-center text-muted-foreground">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
        </td>
        <td className="px-4 py-3 font-medium">{result.case_name}</td>
        <td className="px-4 py-3">
          <HttpMethodBadge method={result.request_method} />
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={result.status} />
        </td>
        <td className="px-4 py-3">
          <span className="tabular-nums">{result.response_status_code ?? "—"}</span>
        </td>
        <td className="px-4 py-3">
          <span className="tabular-nums">{result.response_time.toFixed(1)} ms</span>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-border bg-muted/30">
          <td colSpan={6} className="px-4 py-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-foreground">请求</h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-muted-foreground">URL： </span>
                    <code className="break-all rounded bg-muted px-1 py-0.5 text-xs">
                      {result.request_url}
                    </code>
                  </div>
                  {result.request_headers && result.request_headers !== "{}" && (
                    <div>
                      <span className="font-medium text-muted-foreground">请求头：</span>
                      <pre className="mt-1 max-h-40 overflow-auto rounded-md border bg-card p-2 text-xs">
                        {formatJson(result.request_headers)}
                      </pre>
                    </div>
                  )}
                  {result.query_params && (
                    <div>
                      <span className="font-medium text-muted-foreground">查询参数：</span>
                      <pre className="mt-1 max-h-40 overflow-auto rounded-md border bg-card p-2 text-xs">
                        {formatJson(result.query_params)}
                      </pre>
                    </div>
                  )}
                  {result.request_body && (
                    <div>
                      <span className="font-medium text-muted-foreground">请求体：</span>
                      <pre className="mt-1 max-h-60 overflow-auto rounded-md border bg-card p-2 text-xs">
                        {formatJson(result.request_body)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-foreground">响应</h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-muted-foreground">状态码： </span>
                    <span
                      className={cn(
                        "font-mono font-semibold",
                        result.response_status_code && result.response_status_code < 400
                          ? "text-emerald-500"
                          : "text-destructive"
                      )}
                    >
                      {result.response_status_code ?? "N/A"}
                    </span>
                  </div>
                  {result.response_headers && result.response_headers !== "{}" && (
                    <div>
                      <span className="font-medium text-muted-foreground">响应头：</span>
                      <pre className="mt-1 max-h-40 overflow-auto rounded-md border bg-card p-2 text-xs">
                        {formatJson(result.response_headers)}
                      </pre>
                    </div>
                  )}
                  {result.response_body && (
                    <div>
                      <span className="font-medium text-muted-foreground">响应体：</span>
                      <pre className="mt-1 max-h-60 overflow-auto rounded-md border bg-card p-2 text-xs">
                        {formatJson(result.response_body)}
                      </pre>
                    </div>
                  )}
                  {result.error_message && (
                    <div>
                      <span className="font-medium text-destructive">错误：</span>
                      <pre className="mt-1 max-h-40 overflow-auto rounded-md border border-destructive/20 bg-destructive/5 p-2 text-xs text-destructive">
                        {result.error_message}
                      </pre>
                    </div>
                  )}
                  {result.retry_count > 0 && (
                    <div>
                      <span className="font-medium text-muted-foreground">重试次数： </span>
                      <span>{result.retry_count}</span>
                    </div>
                  )}
                  {result.started_at && result.finished_at && (
                    <div>
                      <span className="font-medium text-muted-foreground">时间： </span>
                      <span className="text-xs text-muted-foreground">
                        {result.started_at} ~ {result.finished_at}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

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
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{test_run.total_cases}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-success">已通过</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-success">{test_run.passed_cases}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-destructive">已失败</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-destructive">{test_run.failed_cases}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">已跳过</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{test_run.skipped_cases}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-warning">错误</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-warning">{test_run.error_cases}</p>
          </CardContent>
        </Card>
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
            <p className="text-2xl font-bold tabular-nums">
              {test_run.total_duration.toFixed(1)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">s</span>
            </p>
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
          <div className="w-full overflow-hidden rounded-md border border-destructive/20">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-destructive/5">
                  <tr>
                    <th className="w-10 px-4 py-3" />
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      用例名称
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">方法</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">状态</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      状态码
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">耗时</th>
                  </tr>
                </thead>
                <tbody>
                  {failedResults.map((r) => (
                    <ExpandableRow key={String(r.id)} result={r} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* All test results */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">
          全部测试结果（{test_results.length}）
        </h2>
        <div className="w-full overflow-hidden rounded-md border border-border">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-card">
                <tr>
                  <th className="w-10 px-4 py-3" />
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                    用例名称
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">方法</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">状态</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">状态码</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">耗时</th>
                </tr>
              </thead>
              <tbody>
                {test_results.map((r) => (
                  <ExpandableRow key={String(r.id)} result={r} />
                ))}
                {test_results.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                      暂无测试结果
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
