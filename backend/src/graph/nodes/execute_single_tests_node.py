"""单接口测试执行节点。

读取 TestCase 列表，顺序执行每条用例，汇总结果交给 TestRunService 收尾。
"""

from typing import Any

from src.core.cache.data_cache import DataCache
from src.core.config import get_config
from src.core.database import get_db_manager
from src.core.logging import get_logger
from src.data.models.test_case import TestCase
from src.data.services import TestCaseService, TestRunService
from src.graph.constants import NodeName
from src.graph.executor.test_executor import TestExecutor
from src.graph.state import AgentState
from src.utils.db_bootstrap import ensure_db

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
    run_id = state.get("run_id", 0)
    logger.info(f"进入单接口测试执行节点，run_id: {run_id}", node=NodeName.EXECUTE_SINGLE_TESTS.value, run_id=run_id)

    if not run_id:
        logger.warning("run_id为空，跳过执行", node=NodeName.EXECUTE_SINGLE_TESTS.value)
        return {"test_results_summary": {}, "next_node": NodeName.ERROR.value, "error_message": "run_id 为空"}

    config = get_config()
    scoped_cache = DataCache.create_scoped(f"run_{run_id}")
    executor = TestExecutor(config, cache=scoped_cache)
    ensure_db()

    with get_db_manager().get_session() as session:
        test_case_service = TestCaseService(session)
        test_run_service = TestRunService(session)

        test_run = test_run_service.get_run(run_id)
        if not test_run:
            logger.error(f"TestRun不存在: run_id={run_id}", node=NodeName.EXECUTE_SINGLE_TESTS.value, run_id=run_id)
            return {
                "test_results_summary": {},
                "error_message": f"TestRun 不存在: {run_id}",
                "next_node": NodeName.ERROR.value,
            }

        test_cases: list[TestCase] = test_case_service.get_active_cases_by_run(run_id)
        if not test_cases:
            logger.warning(f"无可执行的用例，run_id: {run_id}", node=NodeName.EXECUTE_SINGLE_TESTS.value, run_id=run_id)
            test_run_service.update_status(run_id, "completed")
            return {"test_results_summary": {"total": 0}, "next_node": NodeName.GENERATE_REPORT.value}

        test_cases.sort(key=lambda tc: _PRIORITY_ORDER.get(tc.priority, 99))
        test_run_service.update_status(run_id, "running")

        passed = failed = skipped = error = 0
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
                logger.error(
                    f"用例执行异常: {test_case.case_id}, 错误: {e}",
                    node=NodeName.EXECUTE_SINGLE_TESTS.value,
                    case_id=test_case.case_id,
                    error=str(e),
                )
                error += 1

        total = passed + failed + skipped + error
        pass_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0.0
        test_run_service.finalize_run(run_id, total, passed, failed, skipped, error, pass_rate)

    summary: dict[str, Any] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "error": error,
        "pass_rate": round(pass_rate, 2),
    }

    logger.info(
        f"[execute_single_tests] 测试执行完成 - 总数: {total}, 通过: {passed}, 失败: {failed}, 跳过: {skipped}, 错误: {error}, 通过率: {pass_rate:.2f}%",
        node=NodeName.EXECUTE_SINGLE_TESTS.value,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        error=error,
        pass_rate=round(pass_rate, 2),
    )

    return {"test_results_summary": summary, "next_node": NodeName.GENERATE_REPORT.value}
