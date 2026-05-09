"""接口挑选节点实现。

使用 LLM Tool Calling 自动查询数据库并智能挑选接口。
"""

import json
import re
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import StructuredTool

from src.core.llm.llm_client import get_llm_client
from src.core.logging import get_logger
from src.graph.state import TestGraphState
from src.graph.tools.db_tools import search_project, get_project_endpoints
from src.prompts.builders.select_endpoints_builder import SelectEndpointsBuilder

logger = get_logger(__name__)

MAX_TOOL_ITERATIONS = 10
AVAILABLE_TOOLS = [
    StructuredTool.from_function(
    func=search_project,
    name="database_search_project",
    description="根据名称搜索项目，支持模糊匹配。返回匹配的项目列表（JSON格式），包含id、name、base_url、description字段。",
), StructuredTool.from_function(
    func=get_project_endpoints,
    name="database_get_project_endpoints",
    description="根据项目ID获取该项目下所有启用的API接口。返回接口列表（JSON格式），包含id、name、path、method、summary、tags字段。",
)]
TOOL_MAP = {t.name: t for t in AVAILABLE_TOOLS}


def select_endpoints_node(state: TestGraphState) -> TestGraphState:
    """
    接口挑选节点。

    通过 LLM Tool Calling 循环：
    1. LLM 决定调用哪个工具
    2. 执行工具获取结果
    3. 将结果反馈给 LLM
    4. 重复直到 LLM 给出最终答案

    Args:
        state: 当前工作流状态

    Returns:
        TestGraphState: 更新后的状态（含 selected_endpoints）
    """
    logger.info("进入接口挑选节点")
    state["current_node"] = "select_endpoints"

    try:
        builder = SelectEndpointsBuilder()
        messages_dicts = builder.build_messages(state["raw_input"])

        llm_client = get_llm_client()
        messages: List[BaseMessage] = llm_client._convert_messages_base(messages_dicts)

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = llm_client.invoke_with_tools(messages, AVAILABLE_TOOLS)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"LLM 调用工具: {tool_name}, 参数: {tool_args}")

                tool_fn = TOOL_MAP.get(tool_name)
                if tool_fn is None:
                    tool_result = json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
                else:
                    tool_result = tool_fn.invoke(tool_args)

                logger.info(f"工具 {tool_name} 返回: {tool_result[:200]}")
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))

        final_content = response.content if response.content else ""
        logger.info(f"LLM 最终输出: {final_content[:500]}")

        selected = _parse_selected_endpoints(final_content)
        state["selected_endpoints"] = selected
        logger.info(f"选中 {len(selected)} 个接口")

    except Exception as e:
        state["error_message"] = f"接口挑选异常: {str(e)}"
        state["selected_endpoints"] = []
        logger.error(state["error_message"])

    return state


def _parse_selected_endpoints(response: str) -> List[Dict[str, Any]]:
    """
    从 LLM 最终响应中解析选中的接口信息。

    Args:
        response: LLM 最终输出文本

    Returns:
        List[Dict[str, Any]]: 选中的接口列表
    """
    json_match = re.search(r'\{[\s\S]*"selected_endpoint_ids"[\s\S]*\}', response)
    if not json_match:
        logger.warning("无法从 LLM 响应中提取 JSON 结果")
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("LLM 响应 JSON 解析失败")
        return []

    endpoint_ids = data.get("selected_endpoint_ids", [])
    if not endpoint_ids:
        return []

    project_id = data.get("project_id")
    project_name = data.get("project_name", "")
    reason = data.get("reason", "")

    result = []
    for eid in endpoint_ids:
        result.append({
            "endpoint_id": eid,
            "project_id": project_id,
            "project_name": project_name,
            "reason": reason,
        })

    return result
