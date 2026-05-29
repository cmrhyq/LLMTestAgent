"""流程测试用例生成节点。

将所有选中的接口信息一次性传给 LLM，让其编排业务流程并生成带顺序依赖的测试用例。
"""

import hashlib
import json
import re
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
from src.graph.nodes.utils import ensure_db, get_model_name, safe_json_loads
from src.graph.state import AgentState
from src.prompts.builders.flow_case_builder import FlowCasePromptBuilder

logger = get_logger(__name__)


def generate_flow_cases_node(state: AgentState) -> dict:
    """流程测试用例生成节点。

    将所有选中的接口信息汇总后一次性传给 LLM，让其编排业务流程测试用例。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 run_id 和 test_cases_count
    """
    selected_endpoints = state.get("selected_endpoints", [])
    logger.info(
        f"进入流程测试用例生成节点，接口数: {len(selected_endpoints)}",
        node="generate_flow_cases",
        endpoint_count=len(selected_endpoints),
    )

    if not selected_endpoints:
        logger.warning("无选中的接口，跳过流程用例生成", node="generate_flow_cases")
        return {"run_id": 0, "test_cases_count": 0, "error_message": "无选中的接口", "current_step": "error"}

    config = get_config()
    llm_client = get_llm_client()
    prompt_builder = FlowCasePromptBuilder()

    ensure_db()

    project_id = selected_endpoints[0].get("project_id")
    endpoint_ids = [ep.get("endpoint_id") for ep in selected_endpoints if ep.get("endpoint_id")]

    with get_db_manager().get_session() as session:
        project_repo = ProjectRepository(session)
        endpoint_repo = EndpointRepository(session)
        test_run_repo = TestRunRepository(session)
        test_case_repo = TestCaseRepository(session)

        project = project_repo.get_by_id(project_id)
        if not project:
            logger.error(f"项目不存在: project_id={project_id}", node="generate_flow_cases", project_id=project_id)
            return {
                "run_id": 0,
                "test_cases_count": 0,
                "error_message": f"项目不存在: project_id={project_id}",
                "current_step": "error",
            }

        base_url = project.base_url.rstrip("/")

        endpoints: list[Endpoint] = endpoint_repo.get_active_by_ids(endpoint_ids)

        if not endpoints:
            logger.error("未查询到有效的接口定义", node="generate_flow_cases", endpoint_ids=endpoint_ids)
            return {
                "run_id": 0,
                "test_cases_count": 0,
                "error_message": "未查询到有效的接口定义",
                "current_step": "error",
            }

        test_run = TestRun(
            project_id=project_id,
            name=f"LLM流程测试-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status="running",
            trigger_type="manual",
            llm_provider=config.llm.provider,
            llm_model=get_model_name(config),
            started_at=datetime.now().isoformat(),
        )
        test_run_repo.add(test_run)
        run_id = test_run.id

        endpoints_info = _build_endpoints_info(endpoints, base_url)

        messages = prompt_builder.build_messages(endpoints_info)
        response_text = llm_client.chat(messages)
        logger.debug(
            f"LLM流程用例响应，长度: {len(response_text)}",
            node="generate_flow_cases",
            response_length=len(response_text),
        )

        cases_data = _parse_flow_response(response_text)
        endpoint_map = {ep.id: ep for ep in endpoints}

        total_cases = 0
        for idx, case_data in enumerate(cases_data, 1):
            endpoint_id = case_data.get("endpoint_id")
            endpoint = endpoint_map.get(endpoint_id)
            if not endpoint:
                logger.warning(
                    f"步骤{idx}引用未知endpoint_id={endpoint_id}，跳过",
                    node="generate_flow_cases",
                    step=idx,
                    endpoint_id=endpoint_id,
                )
                continue

            full_url = f"{base_url}{endpoint.path}"
            case = _build_flow_test_case(
                case_data=case_data,
                endpoint=endpoint,
                full_url=full_url,
                run_id=run_id,
                idx=idx,
            )
            test_case_repo.add(case)
            total_cases += 1

        test_run.total_cases = total_cases
        logger.info(
            f"流程用例生成完成 - run_id: {run_id}, 总用例数: {total_cases}",
            node="generate_flow_cases",
            run_id=run_id,
            total_cases=total_cases,
        )

    return {"run_id": run_id, "test_cases_count": total_cases, "current_step": "execute_flow_tests"}


def _build_endpoints_info(endpoints: list[Endpoint], base_url: str) -> list[dict[str, Any]]:
    """构建传给 LLM 的接口信息列表。"""
    result = []
    for ep in endpoints:
        info: dict[str, Any] = {
            "endpoint_id": ep.id,
            "name": ep.name,
            "url": f"{base_url}{ep.path}",
            "method": ep.method,
            "description": ep.description or ep.summary or "",
            "headers": safe_json_loads(ep.headers, {}),
            "body": safe_json_loads(ep.body, None),
            "params": safe_json_loads(ep.params, None),
            "responses": safe_json_loads(ep.responses, []),
        }
        result.append(info)
    return result


def _build_flow_test_case(
    case_data: dict[str, Any],
    endpoint: Endpoint,
    full_url: str,
    run_id: int,
    idx: int,
) -> TestCase:
    """从 LLM 输出的单步流程用例数据构造 TestCase ORM 对象。"""
    step_order = case_data.get("step_order", idx)
    case_name = case_data.get("case_name", f"flow_step_{step_order:03d}_{endpoint.name}")
    scenario_type = case_data.get("scenario_type", "normal")
    priority = case_data.get("priority", "P0")
    case_headers = case_data.get("headers", {})
    case_body = case_data.get("body")
    case_params = case_data.get("params")
    assert_rules = case_data.get("assert_rules", ["status_code == 200"])
    expected_result = case_data.get("expected_result", "成功")
    description = case_data.get("description", "")
    cache_rules = case_data.get("cache_rules")

    case_id = f"{endpoint.operation_id}_flow_{step_order:03d}"

    body_str = json.dumps(case_body, ensure_ascii=False) if case_body is not None else None
    unique_content = f"flow|{full_url}|{endpoint.method}|{step_order}|{body_str or ''}"
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
        else "normal",
        priority=priority if priority in ("P0", "P1", "P2") else "P0",
        headers=json.dumps(case_headers, ensure_ascii=False),
        body=body_str,
        params=json.dumps(case_params, ensure_ascii=False) if case_params else None,
        cache_rules=json.dumps(cache_rules, ensure_ascii=False) if cache_rules else None,
        assert_rules=json.dumps(assert_rules, ensure_ascii=False),
        expected_result=expected_result,
        description=description,
        remark=f"LLM流程生成-步骤{step_order}",
        unique_hash=unique_hash,
        generated_by="llm",
    )


def _parse_flow_response(response: str) -> list[dict[str, Any]]:
    """从 LLM 响应中解析流程测试用例。

    支持 markdown code block 和纯 JSON 两种格式。
    """
    response = response.strip()

    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
    else:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start == -1 or json_end <= 0:
            logger.warning("LLM流程响应中未找到JSON内容", node="generate_flow_cases")
            return []
        json_str = response[json_start:json_end]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"解析LLM流程JSON响应失败: {e}", node="generate_flow_cases", error=str(e))
        return []

    if isinstance(data, dict):
        cases = data.get("test_cases", [])
        if isinstance(cases, list):
            cases.sort(key=lambda c: c.get("step_order", 0))
            return cases
        return []

    if isinstance(data, list):
        data.sort(key=lambda c: c.get("step_order", 0))
        return data

    return []
