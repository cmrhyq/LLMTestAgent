"""报告生成节点。

根据 run_id 读取 TestResult 数据，调用 ``src.graph.report`` 渲染
HTML 测试报告并落库。
"""

from pathlib import Path

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.models.report import Report
from src.data.services import ReportService, TestResultService, TestRunService
from data.constant.constants import NodeName
from src.graph.report import render_report
from src.graph.state import AgentState
from src.utils.db_bootstrap import ensure_db

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
    logger.info(f"进入报告生成节点，run_id: {run_id}", node=NodeName.GENERATE_REPORT.value, run_id=run_id)

    if not run_id:
        logger.warning("run_id为空，跳过报告生成", node=NodeName.GENERATE_REPORT.value)
        return {"report_path": "", "next_node": NodeName.ERROR.value}

    config = get_config()
    ensure_db()

    try:
        with get_db_manager().get_session() as session:
            test_result_service = TestResultService(session)
            test_run_service = TestRunService(session)

            test_run = test_run_service.get_run(run_id)
            if not test_run:
                logger.error(f"TestRun不存在: run_id={run_id}", node=NodeName.GENERATE_REPORT.value, run_id=run_id)
                return {
                    "report_path": "",
                    "error_message": f"TestRun 不存在: {run_id}",
                    "next_node": NodeName.ERROR.value,
                }

            results = test_result_service.get_results_by_run(run_id)
            logger.info(
                f"[generate_report] 报告数据汇总 - 结果数: {len(results)}",
                node=NodeName.GENERATE_REPORT.value,
                run_id=run_id,
                result_count=len(results),
            )

            report_content = render_report(test_run, results)

            output_dir = Path(config.output.get_reports_dir())
            output_dir.mkdir(parents=True, exist_ok=True)
            report_file = output_dir / f"test_report_{run_id}.html"
            report_file.write_text(report_content, encoding="utf-8")

            report_path = str(report_file)
            report_record = Report(
                run_id=run_id,
                format="html",
                file_path=report_path,
                file_size=report_file.stat().st_size,
            )
            ReportService(session).create_report(report_record)

            logger.info(f"报告生成成功: {report_path}", node=NodeName.GENERATE_REPORT.value, path=report_path)
            return {"next_node": NodeName.END.value, "report_path": report_path}

    except Exception as e:
        logger.error(f"报告生成异常: {str(e)}", node=NodeName.GENERATE_REPORT.value, error=str(e))
        return {"next_node": NodeName.ERROR.value, "report_path": "", "error_message": f"报告生成异常: {str(e)}"}
