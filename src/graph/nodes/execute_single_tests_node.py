"""单接口测试执行节点。

读取 TestCase 列表，顺序执行每条用例，汇总结果更新 TestRun。
"""

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select

from src.core.cache.data_cache import DataCache
from src.core.config import get_config
from src.core.database import get_db_manager
from src.core.logging import get_logger
from src.data.models.test_case import TestCase
from src.data.models.test_run import TestRun
from src.graph.executor.test_executor import TestExecutor
from src.graph.nodes.utils import ensure_db
from src.graph.state import AgentState

logger = get_logger(__name__)

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def execute_single_tests_node(state: AgentState) -> dict:
    """单接口测试执行节点。

    根据 run_id 查询所有 TestCase，顺序执行并写入 TestResult。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 test_results_summary
    """
    logger.info("进入单接口测试执行节点")

    run_id = state.get("run_id", 0)
    if not run_id:
        logger.warning("run_id 为空，跳过执行")
        return {"test_results_summary": {}}

    config = get_config()
    executor = TestExecutor(config)

    DataCache.get_instance().clear()

    ensure_db()

    with get_db_manager().get_session() as session:
        test_run = session.get(TestRun, run_id)
        if not test_run:
            logger.error(f"TestRun 不存在: run_id={run_id}")
            return {"test_results_summary": {}, "error_message": f"TestRun 不存在: {run_id}"}

        stmt = select(TestCase).where(
            TestCase.run_id == run_id,
            TestCase.status == 1,
        )
        test_cases: List[TestCase] = list(session.scalars(stmt).all())

        if not test_cases:
            logger.warning(f"无可执行的用例: run_id={run_id}")
            test_run.status = "completed"
            test_run.finished_at = datetime.now().isoformat()
            return {"test_results_summary": {"total": 0}}

        test_cases.sort(key=lambda tc: _PRIORITY_ORDER.get(tc.priority, 99))

        test_run.status = "running"
        test_run.started_at = datetime.now().isoformat()
        session.flush()

        passed = 0
        failed = 0
        skipped = 0
        error = 0

        for test_case in test_cases:
            try:
                result = executor.execute_single(test_case, run_id, session)
                session.flush()

                if result.status == "passed":
                    passed += 1
                elif result.status == "failed":
                    failed += 1
                elif result.status == "skipped":
                    skipped += 1
                else:
                    error += 1
            except Exception as e:
                logger.error(f"用例执行异常 [{test_case.case_id}]: {e}")
                error += 1

        total = passed + failed + skipped + error
        pass_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0.0

        test_run.status = "completed"
        test_run.finished_at = datetime.now().isoformat()
        test_run.passed_cases = passed
        test_run.failed_cases = failed
        test_run.skipped_cases = skipped
        test_run.error_cases = error
        test_run.pass_rate = round(pass_rate, 2)

        if test_run.started_at and test_run.finished_at:
            start = datetime.fromisoformat(test_run.started_at)
            end = datetime.fromisoformat(test_run.finished_at)
            test_run.total_duration = (end - start).total_seconds()

    summary: Dict[str, Any] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "error": error,
        "pass_rate": round(pass_rate, 2),
    }

    logger.info(
        f"测试执行完成: total={total}, passed={passed}, "
        f"failed={failed}, skipped={skipped}, error={error}, "
        f"pass_rate={pass_rate:.2f}%"
    )

    return {"test_results_summary": summary}
