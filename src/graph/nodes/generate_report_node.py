"""报告生成节点。

根据 run_id 从数据库读取 TestResult，生成 Markdown 格式测试报告。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.models.test_result import TestResult
from src.data.models.test_run import TestRun
from src.graph.nodes.utils import ensure_db
from src.graph.state import AgentState

logger = get_logger(__name__)


def generate_report_node(state: AgentState) -> dict:
    """报告生成节点。

    根据 run_id 读取 TestResult 数据，生成 Markdown 测试报告。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 report_path 字段
    """
    run_id = state.get("run_id", 0)
    logger.info(f"进入报告生成节点，run_id: {run_id}", node="generate_report", run_id=run_id)

    if not run_id:
        logger.warning(f"run_id为空，跳过报告生成", node="generate_report")
        return {"report_path": ""}

    config = get_config()
    ensure_db()

    try:
        with get_db_manager().get_session() as session:
            test_run = session.get(TestRun, run_id)
            if not test_run:
                logger.error(f"TestRun不存在: run_id={run_id}", node="generate_report", run_id=run_id)
                return {"report_path": "", "error_message": f"TestRun 不存在: {run_id}"}

            stmt = select(TestResult).where(TestResult.run_id == run_id)
            results: List[TestResult] = list(session.scalars(stmt).all())

            logger.info(
                f"[generate_report] 报告数据汇总 - 结果数: {len(results)}, 通过: {test_run.passed_cases}, 失败: {test_run.failed_cases}",
                node="generate_report", run_id=run_id, result_count=len(results),
                passed=test_run.passed_cases, failed=test_run.failed_cases,
            )

            report_content = _build_markdown_report(test_run, results)

            output_dir = Path(config.output.reports_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            report_file = output_dir / f"test_report_{run_id}.md"
            report_file.write_text(report_content, encoding="utf-8")

            report_path = str(report_file)
            logger.info(f"报告生成成功: {report_path}", node="generate_report", path=report_path)
            return {
                "current_step": "end",
                "report_path": report_path
            }

    except Exception as e:
        logger.error(f"报告生成异常: {str(e)}", node="generate_report", error=str(e))
        return {
            "current_step": "error",
            "report_path": "",
            "error_message": f"报告生成异常: {str(e)}"
        }


def _build_markdown_report(test_run: TestRun, results: List[TestResult]) -> str:
    """构建 Markdown 格式测试报告。"""
    lines: List[str] = []

    lines.append("# API 自动化测试报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**测试批次**: {test_run.name}")
    lines.append(f"**LLM 模型**: {test_run.llm_provider} / {test_run.llm_model}")
    lines.append("")

    lines.append("## 测试摘要")
    lines.append("")
    total = test_run.total_cases or len(results)
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总用例数 | {total} |")
    lines.append(f"| 通过 | {test_run.passed_cases} |")
    lines.append(f"| 失败 | {test_run.failed_cases} |")
    lines.append(f"| 跳过 | {test_run.skipped_cases} |")
    lines.append(f"| 错误 | {test_run.error_cases} |")
    lines.append(f"| 通过率 | {test_run.pass_rate:.2f}% |")
    lines.append(f"| 总耗时 | {test_run.total_duration:.2f}s |")
    lines.append("")

    if not results:
        lines.append("*无测试结果数据*")
        return "\n".join(lines)

    failed_results = [r for r in results if r.status in ("failed", "error")]
    if failed_results:
        lines.append("## 失败/错误用例")
        lines.append("")
        lines.append("| 用例ID | 用例名称 | 状态 | 响应码 | 错误信息 |")
        lines.append("|--------|---------|------|--------|---------|")
        for r in failed_results:
            error_short = (r.error_message or "")[:80].replace("|", "\\|")
            lines.append(
                f"| {r.case_id} | {r.case_name} | {r.status} | "
                f"{r.response_status_code or '-'} | {error_short} |"
            )
        lines.append("")

    lines.append("## 全部用例详情")
    lines.append("")
    lines.append("| # | 用例ID | 用例名称 | 状态 | 响应码 | 响应时间(ms) |")
    lines.append("|---|--------|---------|------|--------|-------------|")
    for idx, r in enumerate(results, 1):
        lines.append(
            f"| {idx} | {r.case_id} | {r.case_name} | {r.status} | "
            f"{r.response_status_code or '-'} | {r.response_time:.2f} |"
        )
    lines.append("")

    response_times = [r.response_time for r in results if r.response_time > 0]
    if response_times:
        lines.append("## 响应时间统计")
        lines.append("")
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        sorted_times = sorted(response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[min(p95_idx, len(sorted_times) - 1)]

        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 平均响应时间 | {avg_time:.2f}ms |")
        lines.append(f"| 最短响应时间 | {min_time:.2f}ms |")
        lines.append(f"| 最长响应时间 | {max_time:.2f}ms |")
        lines.append(f"| P95 响应时间 | {p95_time:.2f}ms |")
        lines.append("")

    lines.append("---")
    lines.append("*由 LLM API 自动化测试工具生成*")

    return "\n".join(lines)
