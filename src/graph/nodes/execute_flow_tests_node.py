"""流程测试执行节点。

按 step_order 严格顺序执行流程用例，在接口间传递上下文数据。
前序步骤失败时，后续依赖步骤标记为 skipped。
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select

from src.core.config import get_config
from src.core.database import get_db_manager
from src.core.logging import get_logger
from src.data.models.test_case import TestCase
from src.data.models.test_run import TestRun
from src.graph.executor.test_executor import TestExecutor
from src.graph.nodes.utils import ensure_db
from src.graph.state import AgentState

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
    logger.info("节点进入, node: execute_flow_tests", node="execute_flow_tests")

    run_id = state.get("run_id", 0)
    if not run_id:
        logger.warning("run_id为空，跳过执行")
        return {"test_results_summary": {}, "current_step": "error", "error_message": "run_id 为空"}

    config = get_config()
    executor = TestExecutor(config)

    ensure_db()

    with get_db_manager().get_session() as session:
        test_run = session.get(TestRun, run_id)
        if not test_run:
            logger.error(f"TestRun不存在, run_id: {run_id}", run_id=run_id)
            return {"test_results_summary": {}, "error_message": f"TestRun 不存在: {run_id}", "current_step": "error"}

        stmt = select(TestCase).where(
            TestCase.run_id == run_id,
            TestCase.status == 1,
        )
        test_cases: List[TestCase] = list(session.scalars(stmt).all())

        if not test_cases:
            logger.warning(f"无可执行的用例, run_id: {run_id}", run_id=run_id)
            test_run.status = "completed"
            test_run.finished_at = datetime.now().isoformat()
            return {"test_results_summary": {"total": 0}, "current_step": "generate_report"}

        test_cases.sort(key=lambda tc: _extract_step_order(tc))

        test_run.status = "running"
        test_run.started_at = datetime.now().isoformat()
        session.flush()

        passed = 0
        failed = 0
        skipped = 0
        error = 0
        failed_cache_keys: Set[str] = set()

        for test_case in test_cases:
            cache_rules = _parse_cache_rules(test_case.cache_rules)

            if _has_dependency_on_failed(cache_rules, failed_cache_keys):
                logger.info(f"用例前置步骤失败，标记为skipped, case_id: {test_case.case_id}", case_id=test_case.case_id)
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
                logger.error(f"流程步骤执行异常, case_id: {test_case.case_id}, error: {e}", case_id=test_case.case_id,
                             error=str(e))
                error += 1
                _mark_extract_keys_failed(cache_rules, failed_cache_keys)

        total = passed + failed + skipped + error
        denominator = total - skipped
        pass_rate = (passed / denominator * 100) if denominator > 0 else 0.0

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
        f"流程测试执行完成, total: {total}, passed: {passed}, failed: {failed}, skipped: {skipped}, error: {error}, pass_rate: {round(pass_rate, 2)}",
        total=total, passed=passed, failed=failed,
        skipped=skipped, error=error, pass_rate=round(pass_rate, 2),
    )

    return {"test_results_summary": summary, "current_step": "generate_report"}


def _extract_step_order(test_case: TestCase) -> int:
    """从 case_id 或 remark 中提取 step_order 用于排序。"""
    parts = test_case.case_id.split("_")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return 0


def _parse_cache_rules(cache_rules_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """安全解析 cache_rules JSON。"""
    if not cache_rules_str:
        return None
    try:
        return json.loads(cache_rules_str)
    except (json.JSONDecodeError, TypeError):
        return None


def _has_dependency_on_failed(
        cache_rules: Optional[Dict[str, Any]],
        failed_keys: Set[str],
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
        cache_rules: Optional[Dict[str, Any]],
        failed_keys: Set[str],
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
    from src.data.models.test_result import TestResult

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
        started_at=datetime.now().isoformat(),
        finished_at=datetime.now().isoformat(),
    )
    session.add(result)
