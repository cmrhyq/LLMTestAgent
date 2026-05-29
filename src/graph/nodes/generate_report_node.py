"""报告生成节点。

根据 run_id 从数据库读取 TestResult，生成 HTML 格式测试报告。
"""

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.models.test_result import TestResult
from src.data.models.test_run import TestRun
from src.data.repositories import TestResultRepository, TestRunRepository
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


def _build_html_report(test_run: TestRun, results: list[TestResult]) -> str:
    """构建 HTML 格式测试报告。"""
    total = test_run.total_cases or len(results)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    failed_results = [r for r in results if r.status in ("failed", "error")]

    response_times = [r.response_time for r in results if r.response_time > 0]
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
      <h2>响应时间统计</h2>
      <div class="metrics">
        <div class="metric-card">
          <div class="metric-value">{avg_time:.2f}<span class="metric-unit">ms</span></div>
          <div class="metric-label">平均响应</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{min_time:.2f}<span class="metric-unit">ms</span></div>
          <div class="metric-label">最短响应</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{max_time:.2f}<span class="metric-unit">ms</span></div>
          <div class="metric-label">最长响应</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{p95_time:.2f}<span class="metric-unit">ms</span></div>
          <div class="metric-label">P95 响应</div>
        </div>
      </div>
    </section>"""

    failures_html = ""
    if failed_results:
        rows = []
        for r in failed_results:
            error_short = _esc((r.error_message or "")[:120])
            rows.append(f"""
          <tr>
            <td><code>{_esc(r.case_id)}</code></td>
            <td>{_esc(r.case_name)}</td>
            <td>{_status_badge(r.status)}</td>
            <td>{_esc(r.response_status_code) if r.response_status_code else "—"}</td>
            <td class="error-cell">{error_short}</td>
          </tr>""")
        failures_html = f"""
    <section class="section">
      <h2 class="section-title-error">失败 / 错误用例</h2>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>用例 ID</th>
              <th>用例名称</th>
              <th>状态</th>
              <th>响应码</th>
              <th>错误信息</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}
          </tbody>
        </table>
      </div>
    </section>"""

    detail_rows = []
    if results:
        for idx, r in enumerate(results, 1):
            detail_rows.append(f"""
          <tr>
            <td>{idx}</td>
            <td><code>{_esc(r.case_id)}</code></td>
            <td>{_esc(r.case_name)}</td>
            <td>{_status_badge(r.status)}</td>
            <td>{_esc(r.response_status_code) if r.response_status_code else "—"}</td>
            <td>{r.response_time:.2f}</td>
          </tr>""")
    else:
        detail_rows.append("""
          <tr><td colspan="6" class="empty-state">暂无测试结果数据</td></tr>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API 自动化测试报告 — {_esc(test_run.name)}</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{
      font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
      background:#FDFAF6;
      color:#2D3436;
      line-height:1.6;
      padding:2rem 1rem;
    }}
    .container{{
      max-width:1100px;
      margin:0 auto;
      background:#FFFFFF;
      border-radius:12px;
      box-shadow:0 1px 3px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);
      padding:3rem;
      border:1px solid #DFD8CD;
    }}
    header{{
      border-bottom:2px solid #DFD8CD;
      padding-bottom:1.5rem;
      margin-bottom:2rem;
    }}
    header h1{{
      font-size:1.75rem;
      font-weight:700;
      color:#2D3436;
      letter-spacing:-.02em;
    }}
    header h1 span{{color:#D35400}}
    .meta{{
      display:flex;
      flex-wrap:wrap;
      gap:.6rem 2rem;
      margin-top:.75rem;
      font-size:.875rem;
      color:#636E72;
    }}
    .meta strong{{color:#2D3436;font-weight:600}}
    .section{{margin-bottom:2.5rem}}
    .section h2{{
      font-size:1.2rem;
      font-weight:600;
      color:#2D3436;
      margin-bottom:1rem;
      padding-bottom:.5rem;
      border-bottom:1px solid #DFD8CD;
    }}
    .section-title-error{{color:#C0392B !important}}
    .metrics{{
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
      gap:1rem;
    }}
    .metric-card{{
      background:#F9F5F0;
      border:1px solid #DFD8CD;
      border-radius:8px;
      padding:1.25rem 1rem;
      text-align:center;
    }}
    .metric-card.highlight{{border-color:#D35400;background:#FEF5F0}}
    .metric-value{{
      font-size:1.5rem;
      font-weight:700;
      color:#2D3436;
    }}
    .metric-unit{{font-size:.75rem;font-weight:400;color:#636E72;margin-left:2px}}
    .metric-label{{
      font-size:.8rem;
      color:#636E72;
      margin-top:.25rem;
      text-transform:uppercase;
      letter-spacing:.05em;
    }}
    .table-wrapper{{
      overflow-x:auto;
      border:1px solid #DFD8CD;
      border-radius:8px;
    }}
    table{{
      width:100%;
      border-collapse:collapse;
      font-size:.875rem;
    }}
    thead{{background:#F9F5F0}}
    th{{
      text-align:left;
      padding:.75rem 1rem;
      font-weight:600;
      color:#2D3436;
      border-bottom:1px solid #DFD8CD;
      white-space:nowrap;
    }}
    td{{
      padding:.65rem 1rem;
      border-bottom:1px solid #EEEAE4;
      vertical-align:middle;
    }}
    tbody tr:last-child td{{border-bottom:none}}
    tbody tr:nth-child(even){{background:#FCFAF7}}
    tbody tr:hover{{background:#F5F0E8}}
    code{{
      font-family:"JetBrains Mono",Consolas,"Courier New",monospace;
      font-size:.8rem;
      background:#F9F5F0;
      padding:.15em .4em;
      border-radius:3px;
      color:#D35400;
    }}
    .badge{{
      display:inline-block;
      padding:.2em .6em;
      border-radius:4px;
      font-size:.75rem;
      font-weight:600;
      text-transform:uppercase;
      letter-spacing:.03em;
    }}
    .badge-passed{{background:#E8F8F0;color:#1E8449}}
    .badge-failed{{background:#FDECEA;color:#C0392B}}
    .badge-error{{background:#FDF2E9;color:#A04000}}
    .badge-skipped{{background:#F0EFEB;color:#636E72}}
    .badge-pending{{background:#F0EFEB;color:#636E72}}
    .badge-running{{background:#EBF5FB;color:#2471A3}}
    .error-cell{{
      max-width:280px;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
      font-size:.8rem;
      color:#636E72;
    }}
    .empty-state{{
      text-align:center;
      padding:2rem;
      color:#636E72;
      font-style:italic;
    }}
    footer{{
      text-align:center;
      padding-top:1.5rem;
      border-top:1px solid #DFD8CD;
      font-size:.8rem;
      color:#636E72;
    }}
    @media print{{
      body{{background:#fff;padding:0}}
      .container{{box-shadow:none;border:none;padding:1rem}}
    }}
    @media(max-width:640px){{
      .container{{padding:1.5rem 1rem}}
      .metrics{{grid-template-columns:repeat(2,1fr)}}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1><span>&#9670;</span> API 自动化测试报告</h1>
      <div class="meta">
        <span><strong>生成时间</strong> {generated_at}</span>
        <span><strong>测试批次</strong> {_esc(test_run.name)}</span>
        <span><strong>LLM 模型</strong> {_esc(test_run.llm_provider)} / {_esc(test_run.llm_model)}</span>
      </div>
    </header>

    <section class="section">
      <h2>测试摘要</h2>
      <div class="metrics">
        <div class="metric-card highlight">
          <div class="metric-value">{total}</div>
          <div class="metric-label">总用例</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" style="color:#27AE60">{test_run.passed_cases}</div>
          <div class="metric-label">通过</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" style="color:#C0392B">{test_run.failed_cases}</div>
          <div class="metric-label">失败</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{test_run.skipped_cases}</div>
          <div class="metric-label">跳过</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{test_run.error_cases}</div>
          <div class="metric-label">错误</div>
        </div>
        <div class="metric-card highlight">
          <div class="metric-value">{test_run.pass_rate:.1f}<span class="metric-unit">%</span></div>
          <div class="metric-label">通过率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{test_run.total_duration:.2f}<span class="metric-unit">s</span></div>
          <div class="metric-label">总耗时</div>
        </div>
      </div>
    </section>
{failures_html}
    <section class="section">
      <h2>全部用例详情</h2>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>用例 ID</th>
              <th>用例名称</th>
              <th>状态</th>
              <th>响应码</th>
              <th>响应时间(ms)</th>
            </tr>
          </thead>
          <tbody>{"".join(detail_rows)}
          </tbody>
        </table>
      </div>
    </section>
{stats_html}
    <footer>
      由 LLM API 自动化测试工具生成 &middot; {generated_at}
    </footer>
  </div>
</body>
</html>
"""
