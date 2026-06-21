"""报告生成节点。

根据 run_id 从数据库读取 TestResult，生成 HTML 格式测试报告。
"""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.models.report import Report
from src.data.models.test_result import TestResult
from src.data.models.test_run import TestRun
from src.data.repositories import ReportRepository, TestResultRepository, TestRunRepository
from src.graph.nodes.utils import ensure_db
from src.graph.state import AgentState

logger = get_logger(__name__)


def generate_report_node(state: AgentState) -> dict:
    """报告生成节点。

    根据 run_id 读取 TestResult 数据，生成 HTML 测试报告。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 report_path 字段
    """
    run_id = state.get("run_id", 0)
    logger.info(f"进入报告生成节点，run_id: {run_id}", node="generate_report", run_id=run_id)

    if not run_id:
        logger.warning("run_id为空，跳过报告生成", node="generate_report")
        return {"report_path": ""}

    config = get_config()
    ensure_db()

    try:
        with get_db_manager().get_session() as session:
            test_result_repo = TestResultRepository(session=session)
            test_run_repo = TestRunRepository(session=session)

            test_run = test_run_repo.get_by_id(run_id)
            if not test_run:
                logger.error(f"TestRun不存在: run_id={run_id}", node="generate_report", run_id=run_id)
                return {"report_path": "", "error_message": f"TestRun 不存在: {run_id}"}

            results: list[TestResult] = test_result_repo.get_by_run(run_id)

            logger.info(
                f"[generate_report] 报告数据汇总 - 结果数: {len(results)}, 通过: {test_run.passed_cases}, 失败: {test_run.failed_cases}",
                node="generate_report",
                run_id=run_id,
                result_count=len(results),
                passed=test_run.passed_cases,
                failed=test_run.failed_cases,
            )

            report_content = _build_html_report(test_run, results)

            output_dir = Path(config.output.reports_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            report_file = output_dir / f"test_report_{run_id}.html"
            report_file.write_text(report_content, encoding="utf-8")

            report_path = str(report_file)
            file_size = report_file.stat().st_size

            report_repo = ReportRepository(session=session)
            report_record = Report(
                run_id=run_id,
                format="html",
                file_path=report_path,
                file_size=file_size,
            )
            report_repo.add(report_record)

            logger.info(f"报告生成成功: {report_path}", node="generate_report", path=report_path)
            return {"current_step": "end", "report_path": report_path}

    except Exception as e:
        logger.error(f"报告生成异常: {str(e)}", node="generate_report", error=str(e))
        return {"current_step": "error", "report_path": "", "error_message": f"报告生成异常: {str(e)}"}


def _esc(text: Any) -> str:
    """对文本做 HTML 转义。"""
    return html.escape(str(text)) if text is not None else ""


def _status_badge(status: str) -> str:
    """根据状态返回对应的 HTML badge。"""
    css_class = {
        "passed": "badge-passed",
        "failed": "badge-failed",
        "error": "badge-error",
        "skipped": "badge-skipped",
        "pending": "badge-pending",
        "running": "badge-running",
    }.get(status, "badge-pending")
    return f'<span class="badge {css_class}">{_esc(status)}</span>'


def _method_badge(method: str) -> str:
    """Return an HTTP method badge."""
    method_text = (method or "").upper()
    css_class = {
        "GET": "method-get",
        "POST": "method-post",
        "PUT": "method-put",
        "PATCH": "method-patch",
        "DELETE": "method-delete",
    }.get(method_text, "method-default")
    return f'<span class="method-badge {css_class}">{_esc(method_text or "N/A")}</span>'


def _format_json(raw: str | None) -> str:
    """Pretty-print a JSON string when possible."""
    if not raw:
        return ""
    try:
        return json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        return raw


def _detail_block(title: str, raw: str | None, *, skip_empty_object: bool = False) -> str:
    """Build an optional detail code block."""
    if not raw or (skip_empty_object and raw == "{}"):
        return ""
    return f"""
              <div class="detail-block">
                <div class="detail-label">{_esc(title)}</div>
                <pre>{_esc(_format_json(raw))}</pre>
              </div>"""


def _result_details(result: TestResult) -> str:
    """Build expandable details for one test result."""
    request_headers = _detail_block("Headers", result.request_headers, skip_empty_object=True)
    query_params = _detail_block("Query Params", result.query_params)
    request_body = _detail_block("Body", result.request_body)
    response_headers = _detail_block("Headers", result.response_headers, skip_empty_object=True)
    response_body = _detail_block("Body", result.response_body)

    error_html = ""
    if result.error_message:
        error_html = f"""
              <div class="detail-block error-detail">
                <div class="detail-label">Error</div>
                <pre>{_esc(result.error_message)}</pre>
              </div>"""

    retries_html = ""
    retry_count = result.retry_count or 0
    if retry_count > 0:
        retries_html = f"""
              <div class="kv-line">
                <span>Retries</span>
                <strong>{retry_count}</strong>
              </div>"""

    time_html = ""
    if result.started_at and result.finished_at:
        time_html = f"""
              <div class="kv-line">
                <span>Time</span>
                <strong>{_esc(result.started_at)} ~ {_esc(result.finished_at)}</strong>
              </div>"""

    status_code_class = "ok" if result.response_status_code and result.response_status_code < 400 else "bad"

    return f'''
          <div class="details-grid">
            <section>
              <h3>Request</h3>
              <div class="kv-line">
                <span>URL</span>
                <code>{_esc(result.request_url)}</code>
              </div>
{request_headers}
{query_params}
{request_body}
            </section>
            <section>
              <h3>Response</h3>
              <div class="kv-line">
                <span>Status Code</span>
                <strong class="{status_code_class}">{_esc(result.response_status_code) if result.response_status_code else "N/A"}</strong>
              </div>
{response_headers}
{response_body}
{error_html}
{retries_html}
{time_html}
            </section>
          </div>'''


def _result_card(result: TestResult) -> str:
    """Build a result row aligned with the frontend report view."""
    return f"""
        <details class="result-row">
          <summary>
            <span class="chevron"></span>
            <span class="case-name">{_esc(result.case_name)}</span>
            <span>{_method_badge(result.request_method)}</span>
            <span>{_status_badge(result.status)}</span>
            <span class="mono">{_esc(result.response_status_code) if result.response_status_code else "&mdash;"}</span>
            <span class="mono">{(result.response_time or 0):.1f} ms</span>
          </summary>
{_result_details(result)}
        </details>"""


def _results_section(title: str, results: list[TestResult], *, danger: bool = False) -> str:
    """Build a result list section."""
    title_class = ' class="danger-title"' if danger else ""
    border_class = " danger-border" if danger else ""
    empty_text = "No failed or error cases" if danger else "No test results available"
    rows = "\n".join(_result_card(result) for result in results)
    if not rows:
        rows = f'<div class="empty-state">{empty_text}</div>'

    return f"""
    <section class="section">
      <h2{title_class}>{_esc(title)} ({len(results)})</h2>
      <div class="results-table{border_class}">
        <div class="table-head">
          <span></span>
          <span>Case Name</span>
          <span>Method</span>
          <span>Status</span>
          <span>Code</span>
          <span>Time</span>
        </div>
{rows}
      </div>
    </section>"""


def _build_html_report(test_run: TestRun, results: list[TestResult]) -> str:
    """Build the offline HTML report aligned with the frontend report view."""
    total = test_run.total_cases or len(results)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    failed_results = [r for r in results if r.status in ("failed", "error")]

    response_times = [r.response_time for r in results if r.response_time and r.response_time > 0]
    stats_html = ""
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        sorted_times = sorted(response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[min(p95_idx, len(sorted_times) - 1)]
        stats_html = f"""
    <section class="section">
      <div class="metric-grid response-grid">
        <div class="metric-card">
          <div class="metric-label">Avg Response</div>
          <div class="metric-value">{avg_time:.1f}<span class="metric-unit">ms</span></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Min Response</div>
          <div class="metric-value">{min_time:.1f}<span class="metric-unit">ms</span></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Max Response</div>
          <div class="metric-value">{max_time:.1f}<span class="metric-unit">ms</span></div>
        </div>
        <div class="metric-card">
          <div class="metric-label">P95 Response</div>
          <div class="metric-value">{p95_time:.1f}<span class="metric-unit">ms</span></div>
        </div>
      </div>
    </section>"""

    failures_html = ""
    if failed_results:
        failures_html = _results_section("Failed / Error Cases", failed_results, danger=True)

    all_results_html = _results_section("All Test Results", results)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API Test Report - {_esc(test_run.name)}</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box}}
    body{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:#ffffff;color:#1f2328;line-height:1.6;margin:0;padding:2rem}}
    .page{{max-width:1280px;margin:0 auto}}
    header{{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:1.5rem}}
    header h1{{margin:0;font-size:1.5rem;font-weight:700;color:#1f2328;letter-spacing:0}}
    .meta{{margin-top:.25rem;font-size:.875rem;color:#656d76}}
    .section{{margin-bottom:1.5rem}}
    .section h2{{font-size:1.125rem;font-weight:600;color:#1f2328;margin:0 0 .75rem}}
    .danger-title{{color:#cf222e !important}}
    .metric-grid{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:1rem}}
    .response-grid{{grid-template-columns:repeat(4,minmax(0,1fr))}}
    .metric-card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:1rem;min-height:88px}}
    .metric-value{{font-size:1.5rem;font-weight:700;color:#1f2328;margin-top:.35rem}}
    .metric-unit{{font-size:.875rem;font-weight:400;color:#656d76;margin-left:.25rem}}
    .metric-label{{font-size:.875rem;color:#656d76;font-weight:500}}
    .success{{color:#1a7f37}} .danger{{color:#cf222e}} .warning{{color:#9a6700}}
    .results-table{{overflow:hidden;border:1px solid #d0d7de;border-radius:6px;background:#ffffff}}
    .danger-border{{border-color:rgba(207,34,46,.4)}}
    .table-head,.result-row summary{{display:grid;grid-template-columns:2.5rem minmax(18rem,1fr) 7rem 7rem 5rem 7rem;align-items:center;gap:0}}
    .table-head{{background:#f6f8fa;border-bottom:1px solid #d0d7de;color:#656d76;font-size:.875rem;font-weight:500}}
    .table-head span,.result-row summary span{{padding:.75rem 1rem}}
    .result-row{{border-bottom:1px solid #d0d7de}}
    .result-row:last-child{{border-bottom:none}}
    .result-row summary{{cursor:pointer;list-style:none;transition:background-color .15s ease}}
    .result-row summary::-webkit-details-marker{{display:none}}
    .result-row summary:hover{{background:#f6f8fa}}
    .chevron::before{{content:"\\203A";display:inline-block;color:#656d76;font-size:1.25rem;transition:transform .15s ease}}
    .result-row[open] .chevron::before{{transform:rotate(90deg)}}
    .case-name{{color:#1f2328;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    code{{font-family:"JetBrains Mono",Consolas,"Courier New",monospace;font-size:.8rem;background:#f6f8fa;border:1px solid #d0d7de;border-radius:4px;color:#1f2328;padding:.15rem .35rem;word-break:break-all}}
    .mono{{font-variant-numeric:tabular-nums;color:#1f2328}}
    .badge{{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.75rem;font-weight:600;text-transform:capitalize;border:1px solid transparent}}
    .badge-passed{{background:rgba(26,127,55,.08);color:#1a7f37;border-color:rgba(26,127,55,.3)}}
    .badge-failed{{background:rgba(207,34,46,.08);color:#cf222e;border-color:rgba(207,34,46,.3)}}
    .badge-error{{background:rgba(154,103,0,.08);color:#9a6700;border-color:rgba(154,103,0,.3)}}
    .badge-skipped,.badge-pending{{background:#f6f8fa;color:#656d76;border-color:#d0d7de}}
    .badge-running{{background:rgba(9,105,218,.08);color:#0969da;border-color:rgba(9,105,218,.3)}}
    .method-badge{{display:inline-block;border-radius:4px;padding:.15rem .5rem;font-size:.75rem;font-weight:700}}
    .method-get{{background:rgba(9,105,218,.08);color:#0969da}}
    .method-post{{background:rgba(26,127,55,.08);color:#1a7f37}}
    .method-put,.method-patch{{background:rgba(154,103,0,.08);color:#9a6700}}
    .method-delete{{background:rgba(207,34,46,.08);color:#cf222e}}
    .method-default{{background:#f6f8fa;color:#656d76}}
    .details-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;background:#f6f8fa;border-top:1px solid #d0d7de;padding:1rem 1.5rem 1.25rem 3.5rem}}
    .details-grid h3{{font-size:.875rem;margin:.1rem 0 .75rem;color:#1f2328}}
    .kv-line{{display:flex;align-items:flex-start;gap:.5rem;margin:.5rem 0;color:#1f2328;font-size:.875rem}}
    .kv-line span{{min-width:6rem;color:#656d76;font-weight:500}}
    .kv-line strong{{font-weight:600;color:#1f2328;word-break:break-all}}
    .ok{{color:#1a7f37 !important}} .bad{{color:#cf222e !important}}
    .detail-block{{margin-top:.75rem}}
    .detail-label{{font-size:.875rem;font-weight:500;color:#656d76;margin-bottom:.35rem}}
    pre{{margin:0;max-height:16rem;overflow:auto;background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:.75rem;color:#1f2328;font-size:.75rem;line-height:1.5;white-space:pre-wrap;word-break:break-word}}
    .error-detail pre{{border-color:rgba(207,34,46,.4);background:rgba(207,34,46,.04);color:#cf222e}}
    .empty-state{{text-align:center;padding:2rem;color:#656d76}}
    footer{{text-align:center;padding:1.5rem 0 .5rem;font-size:.8rem;color:#656d76}}
    @media print{{body{{background:#fff;color:#111;padding:1rem}}.metric-card,.results-table,pre,code{{border-color:#ddd}}.metric-card,.table-head,pre,code{{background:#fff}}}}
    @media(max-width:980px){{body{{padding:1rem}}header{{display:block}}.metric-grid,.response-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.table-head{{display:none}}.result-row summary{{grid-template-columns:2.25rem minmax(0,1fr)}}.result-row summary span:nth-child(n+3){{grid-column:2;padding-top:.15rem;padding-bottom:.15rem}}.details-grid{{grid-template-columns:1fr;padding:1rem}}}}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <div>
        <h1>{_esc(test_run.name)}</h1>
        <div class="meta">{_esc(test_run.llm_provider)} / {_esc(test_run.llm_model)} &middot; Generated {generated_at}</div>
      </div>
    </header>
    <section class="section">
      <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Total</div><div class="metric-value">{total}</div></div>
        <div class="metric-card"><div class="metric-label success">Passed</div><div class="metric-value success">{test_run.passed_cases}</div></div>
        <div class="metric-card"><div class="metric-label danger">Failed</div><div class="metric-value danger">{test_run.failed_cases}</div></div>
        <div class="metric-card"><div class="metric-label">Skipped</div><div class="metric-value">{test_run.skipped_cases}</div></div>
        <div class="metric-card"><div class="metric-label warning">Error</div><div class="metric-value warning">{test_run.error_cases}</div></div>
        <div class="metric-card"><div class="metric-label">Pass Rate</div><div class="metric-value">{test_run.pass_rate:.1f}<span class="metric-unit">%</span></div></div>
        <div class="metric-card"><div class="metric-label">Duration</div><div class="metric-value">{test_run.total_duration:.2f}<span class="metric-unit">s</span></div></div>
      </div>
    </section>
{stats_html}
{failures_html}
{all_results_html}
    <footer>Generated by LLMTestAgent &middot; {generated_at}</footer>
  </div>
</body>
</html>
"""
