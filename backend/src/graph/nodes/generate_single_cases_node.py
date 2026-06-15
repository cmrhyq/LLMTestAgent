"""单接口测试用例生成节点。

根据选中的 Endpoint 信息，逐个调用 LLM 生成测试用例并写入数据库。
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.llm.llm_client import get_llm_client
from src.core.logging import get_logger
from src.data.models.endpoint import Endpoint
from src.data.models.test_case import TestCase
from src.data.models.test_run import TestRun
from src.data.repositories import EndpointRepository, ProjectRepository, TestCaseRepository, TestRunRepository
from src.graph.nodes.utils import ensure_db, get_model_name, parse_llm_json_response, safe_json_loads
from src.graph.state import AgentState
from src.prompts.builders.case_builder import CasePromptBuilder
from src.prompts.formatters.case_formatter import format_scenario_types

logger = get_logger(__name__)


def generate_single_cases_node(state: AgentState) -> dict:
    """单接口测试用例生成节点。

    从 selected_endpoints 获取接口信息，逐个调用 LLM 生成用例，写入数据库。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 run_id 和 test_cases_count
    """
    selected_endpoints = state.get("selected_endpoints", [])
    logger.info(
        f"进入单接口测试用例生成节点，接口数: {len(selected_endpoints)}",
        node="generate_single_cases",
        endpoint_count=len(selected_endpoints),
    )

    if not selected_endpoints:
        logger.warning("无选中的接口，跳过用例生成", node="generate_single_cases")
        return {"run_id": 0, "test_cases_count": 0, "error_message": "无选中的接口", "current_step": "error"}

    config = get_config()
    llm_client = get_llm_client()
    prompt_builder = CasePromptBuilder()

    ensure_db()

    project_id = int(selected_endpoints[0].get("project_id", 0))
    endpoint_ids = [int(ep["endpoint_id"]) for ep in selected_endpoints if ep.get("endpoint_id")]

    with get_db_manager().get_session() as session:
        project_repo = ProjectRepository(session)
        endpoint_repo = EndpointRepository(session)
        test_run_repo = TestRunRepository(session)
        test_case_repo = TestCaseRepository(session)

        project = project_repo.get_by_id(project_id)
        if not project:
            logger.error(f"项目不存在: project_id={project_id}", node="generate_single_cases", project_id=project_id)
            return {
                "run_id": 0,
                "test_cases_count": 0,
                "error_message": f"项目不存在: project_id={project_id}",
                "current_step": "error",
            }

        base_url = project.base_url.rstrip("/")

        endpoints: list[Endpoint] = endpoint_repo.get_active_by_ids(endpoint_ids)

        if not endpoints:
            logger.error("未查询到有效的接口定义", node="generate_single_cases", endpoint_ids=endpoint_ids)
            return {
                "run_id": 0,
                "test_cases_count": 0,
                "error_message": "未查询到有效的接口定义",
                "current_step": "error",
            }

        test_run = TestRun(
            project_id=project_id,
            name=f"LLM测试-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status="running",
            trigger_type="manual",
            llm_provider=config.llm.provider,
            llm_model=get_model_name(config),
            started_at=datetime.now().isoformat(),
        )
        test_run_repo.add(test_run)
        run_id = test_run.id

        total_cases = 0
        scenario_types_text = format_scenario_types(config.case_generation.scenarios)

        for endpoint in endpoints:
            try:
                cases = _generate_cases_for_endpoint(
                    endpoint=endpoint,
                    base_url=base_url,
                    run_id=run_id,
                    scenario_types_text=scenario_types_text,
                    prompt_builder=prompt_builder,
                    llm_client=llm_client,
                    test_case_repo=test_case_repo,
                )
                total_cases += len(cases)
                logger.info(
                    f"接口用例生成完成: {endpoint.name}，生成{len(cases)}个用例",
                    node="generate_single_cases",
                    endpoint=endpoint.name,
                    count=len(cases),
                )
            except Exception as e:
                logger.error(
                    f"接口用例生成失败: {endpoint.name}，错误: {e}",
                    node="generate_single_cases",
                    endpoint=endpoint.name,
                    error=str(e),
                )

        test_run.total_cases = total_cases
        logger.info(
            f"用例生成完成 - run_id: {run_id}, 总用例数: {total_cases}",
            node="generate_single_cases",
            run_id=run_id,
            total_cases=total_cases,
        )

    return {"run_id": run_id, "test_cases_count": total_cases, "current_step": "execute_single_tests"}


def _generate_cases_for_endpoint(
    endpoint: Endpoint,
    base_url: str,
    run_id: int,
    scenario_types_text: str,
    prompt_builder: CasePromptBuilder,
    llm_client: Any,
    test_case_repo: TestCaseRepository,
) -> list[TestCase]:
    """为单个 Endpoint 生成测试用例。"""
    full_url = f"{base_url}{endpoint.path}"

    headers = safe_json_loads(endpoint.headers, {})
    body = safe_json_loads(endpoint.body, None)
    params = safe_json_loads(endpoint.params, None)

    default_assert_rules = _extract_default_asserts(endpoint.responses)

    api_info = {
        "name": endpoint.name,
        "url": full_url,
        "method": endpoint.method,
        "headers": headers,
        "body": body,
        "params": params,
        "assert_rules": default_assert_rules,
        "priority": "P1",
        "description": endpoint.description or endpoint.summary or "",
    }

    system_prompt = prompt_builder.build_system_prompt()
    user_prompt = prompt_builder.build_user_prompt(api_info, scenario_types_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response_text = llm_client.chat(messages)
    cases_data = parse_llm_json_response(response_text)

    orm_cases: list[TestCase] = []
    for idx, case_data in enumerate(cases_data, 1):
        case = _build_test_case_orm(
            case_data=case_data,
            endpoint=endpoint,
            full_url=full_url,
            run_id=run_id,
            idx=idx,
            default_assert_rules=default_assert_rules,
        )
        test_case_repo.add(case)
        orm_cases.append(case)

    return orm_cases


def _build_test_case_orm(
    case_data: dict[str, Any],
    endpoint: Endpoint,
    full_url: str,
    run_id: int,
    idx: int,
    default_assert_rules: list[str],
) -> TestCase:
    """从 LLM 输出的单条用例数据构造 TestCase ORM 对象。"""
    case_name = case_data.get("case_name", f"{endpoint.name}_case_{idx:03d}")
    scenario_type = case_data.get("scenario_type", "normal")
    priority = case_data.get("priority", "P1")
    case_headers = case_data.get("headers", {})
    case_body = case_data.get("body")
    case_params = case_data.get("params")
    assert_rules = case_data.get("assert_rules", default_assert_rules)
    expected_result = case_data.get("expected_result", "成功")
    description = case_data.get("description", "")
    cache_rules = case_data.get("cache_rules")

    case_id = f"{endpoint.operation_id}_llm_{idx:03d}"

    body_str = json.dumps(case_body, ensure_ascii=False) if case_body is not None else None
    unique_content = f"{full_url}|{endpoint.method}|{body_str or ''}"
    unique_hash = hashlib.md5(unique_content.encode()).hexdigest()[:8]

    return TestCase(
        run_id=run_id,
        endpoint_id=endpoint.id,
        case_id=case_id,
        case_name=case_name,
        url=full_url,
        method=endpoint.method,
        scenario_type=scenario_type
        if scenario_type
        in ("normal", "param_missing", "param_type_error", "boundary_value", "permission_error", "custom")
        else "custom",
        priority=priority if priority in ("P0", "P1", "P2") else "P1",
        headers=json.dumps(case_headers, ensure_ascii=False),
        body=body_str,
        params=json.dumps(case_params, ensure_ascii=False) if case_params else None,
        cache_rules=json.dumps(cache_rules, ensure_ascii=False) if cache_rules else None,
        assert_rules=json.dumps(assert_rules, ensure_ascii=False),
        expected_result=expected_result,
        description=description,
        remark="LLM生成",
        unique_hash=unique_hash,
        generated_by="llm",
    )


def _extract_default_asserts(responses_json: str | None) -> list[str]:
    """从 Endpoint.responses 字段提取默认断言规则。"""
    default_rules = ["status_code == 200"]

    if not responses_json:
        return default_rules

    try:
        responses = json.loads(responses_json)
    except (json.JSONDecodeError, TypeError):
        return default_rules

    if not responses:
        return default_rules

    for resp in responses:
        status_code = str(resp.get("status_code", ""))
        if status_code.startswith("2"):
            default_rules = [f"status_code == {status_code}"]
            content = resp.get("content", {})
            if content:
                for media_data in content.values():
                    schema = media_data.get("schema", {})
                    props = schema.get("properties", {})
                    if "code" in props:
                        default_rules.append("$.code == 200")
                    break
            break

    return default_rules
