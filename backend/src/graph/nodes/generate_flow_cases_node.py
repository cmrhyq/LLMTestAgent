"""流程测试用例生成节点。

基于 ``BaseCaseGenerationNode`` 模板方法，差异点：
- 所有选中接口一次性传给 LLM 编排业务流程
- case_id 规则：``{operation_id}_flow_{step_order}``
"""

from typing import Any

from src.core.logging import get_logger
from src.data.models.endpoint import Endpoint
from src.data.models.test_case import TestCase
from src.data.services import CaseGenerationService
from data.constant.constants import NodeName
from src.graph.nodes.base_case_generation import BaseCaseGenerationNode
from src.prompts.builders.flow_case_builder import FlowCasePromptBuilder
from src.utils.json_utils import parse_llm_json_response, safe_json_loads

logger = get_logger(__name__)


class GenerateFlowCasesNode(BaseCaseGenerationNode):
    """流程测试用例生成节点。"""

    run_name_prefix = "LLM流程测试"
    next_node_on_success = NodeName.EXECUTE_FLOW_TESTS

    def _generate_cases(
        self,
        *,
        endpoints: list[Endpoint],
        base_url: str,
        run_id: int,
        llm_client: Any,
        case_service: CaseGenerationService,
    ) -> list[TestCase]:
        prompt_builder = FlowCasePromptBuilder()
        endpoints_info = self._build_endpoints_info(endpoints, base_url)

        messages = prompt_builder.build_messages(endpoints_info)
        response_text = llm_client.chat(messages)
        logger.debug(
            f"LLM流程用例响应，长度: {len(response_text)}",
            node="generate_flow_cases",
            response_length=len(response_text),
        )

        cases_data = parse_llm_json_response(response_text, sort_key="step_order")
        endpoint_map = {ep.id: ep for ep in endpoints}

        cases: list[TestCase] = []
        for idx, case_data in enumerate(cases_data, 1):
            endpoint_id = case_data.get("endpoint_id")
            endpoint = endpoint_map.get(endpoint_id) if isinstance(endpoint_id, int) else None
            if not endpoint:
                logger.warning(
                    f"步骤{idx}引用未知endpoint_id={endpoint_id}，跳过",
                    node="generate_flow_cases",
                    step=idx,
                    endpoint_id=endpoint_id,
                )
                continue
            cases.append(
                case_service.build_flow_case(
                    case_data=case_data,
                    endpoint=endpoint,
                    full_url=f"{base_url}{endpoint.path}",
                    run_id=run_id,
                    idx=idx,
                )
            )
        return cases

    @staticmethod
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


generate_flow_cases_node = GenerateFlowCasesNode()
