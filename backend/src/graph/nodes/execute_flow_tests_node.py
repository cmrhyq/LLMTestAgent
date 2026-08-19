"""流程测试执行节点。

按 step_order 严格顺序执行流程用例，在接口间传递上下文数据。
前序步骤失败时，后续依赖步骤标记为 skipped。
"""

from typing import Any

from src.core.cache.data_cache import DataCache
from src.core.config import get_config
from src.core.database import get_db_manager
from src.core.logging import get_logger
from src.data.models.base import local_now
from src.data.models.test_case import TestCase
from src.data.models.test_result import TestResult
from src.data.services import TestCaseService, TestRunService
from src.graph.constants import NodeName
from src.graph.executor.test_executor import TestExecutor
from src.graph.state import AgentState
from src.utils.db_bootstrap import ensure_db
from src.utils.json_utils import safe_json_loads

logger = get_logger(__name__)


def execute_flow_tests_node(state: AgentState) -> dict:
    """流程测试执行节点。

    按 step_order 顺序执行用例，保留 DataCache 跨步骤上下文。
    前序步骤失败后，依赖其输出的后续步骤标记为 skipped。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 test_results_summary
    """
    run_id = state.get("run_id", 0)
    logger.info(f"进入流程测试执行节点，run_id: {run_id}", node=NodeName.EXECUTE_FLOW_TESTS.value, run_id=run_id)

    if not run_id:
        logger.warning("run_id为空，跳过执行", node=NodeName.EXECUTE_FLOW_TESTS.value)
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
            logger.error(f"TestRun不存在: run_id={run_id}", node=NodeName.EXECUTE_FLOW_TESTS.value, run_id=run_id)
            return {
                "test_results_summary": {},
                "error_message": f"TestRun 不存在: {run_id}",
                "next_node": NodeName.ERROR.value,
            }

        test_cases: list[TestCase] = test_case_service.get_active_cases_by_run(run_id)
        if not test_cases:
            logger.warning(f"无可执行的用例，run_id: {run_id}", node=NodeName.EXECUTE_FLOW_TESTS.value, run_id=run_id)
            test_run_service.update_status(run_id, "completed")
            return {"test_results_summary": {"total": 0}, "next_node": NodeName.GENERATE_REPORT.value}

        test_cases.sort(key=_extract_step_order)
        test_run_service.update_status(run_id, "running")

        passed = failed = skipped = error = 0
        failed_cache_keys: set[str] = set()

        for test_case in test_cases:
            cache_rules = safe_json_loads(test_case.cache_rules, None)

            if _has_dependency_on_failed(cache_rules, failed_cache_keys):
                logger.info(
                    f"用例前置步骤失败，标记为skipped: {test_case.case_id}",
                    node=NodeName.EXECUTE_FLOW_TESTS.value,
                    case_id=test_case.case_id,
                )
                _record_skipped(test_case, run_id, session, "前置步骤失败，跳过执行")
                skipped += 1
                _mark_extract_keys_failed(cache_rules, failed_cache_keys)
                continue

            try:
                result = executor.execute_single(test_case, run_id, session)
                session.flush()
                if result.status == "passed":
                    passed += 1
                elif result.status == "failed":
                    failed += 1
                    _mark_extract_keys_failed(cache_rules, failed_cache_keys)
                elif result.status == "skipped":
                    skipped += 1
                    _mark_extract_keys_failed(cache_rules, failed_cache_keys)
                else:
                    error += 1
                    _mark_extract_keys_failed(cache_rules, failed_cache_keys)
            except Exception as e:
                logger.error(
                    f"流程步骤执行异常: {test_case.case_id}, 错误: {e}",
                    node=NodeName.EXECUTE_FLOW_TESTS.value,
                    case_id=test_case.case_id,
                    error=str(e),
                )
                error += 1
                _mark_extract_keys_failed(cache_rules, failed_cache_keys)

        total = passed + failed + skipped + error
        denominator = total - skipped
        pass_rate = (passed / denominator * 100) if denominator > 0 else 0.0
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
        f"[execute_flow_tests] 流程测试执行完成 - 总数: {total}, 通过: {passed}, 失败: {failed}, 跳过: {skipped}, 错误: {error}, 通过率: {pass_rate:.2f}%",
        node=NodeName.EXECUTE_FLOW_TESTS.value,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        error=error,
        pass_rate=round(pass_rate, 2),
    )

    return {"test_results_summary": summary, "next_node": NodeName.GENERATE_REPORT.value}


def _extract_step_order(test_case: TestCase) -> int:
    """从 case_id 或 remark 中提取 step_order 用于排序。"""
    parts = test_case.case_id.split("_")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return 0


def _has_dependency_on_failed(
    cache_rules: dict[str, Any] | None,
    failed_keys: set[str],
) -> bool:
    """检查当前步骤是否依赖已失败步骤产出的缓存键。"""
    if not cache_rules or not failed_keys:
        return False

    inject_rules = cache_rules.get("inject", [])
    for rule in inject_rules:
        cache_key = rule.get("cache_key", "")
        if cache_key in failed_keys:
            return True
    return False


def _mark_extract_keys_failed(
    cache_rules: dict[str, Any] | None,
    failed_keys: set[str],
) -> None:
    """将当前步骤本应产出的 cache_key 标记为失败。"""
    if not cache_rules:
        return

    extract_rules = cache_rules.get("extract", [])
    for rule in extract_rules:
        cache_key = rule.get("cache_key", "")
        if cache_key:
            failed_keys.add(cache_key)


def _record_skipped(
    test_case: TestCase,
    run_id: int,
    session: Any,
    reason: str,
) -> None:
    """为跳过的用例记录一条 TestResult。"""
    result = TestResult(
        run_id=run_id,
        test_case_id=test_case.id,
        case_id=test_case.case_id,
        case_name=test_case.case_name,
        status="skipped",
        request_url=test_case.url,
        request_method=test_case.method,
        request_headers="{}",
        response_headers="{}",
        error_message=reason,
        started_at=local_now(),
        finished_at=local_now(),
    )
    session.add(result)
