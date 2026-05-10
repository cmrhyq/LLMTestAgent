"""接口挑选节点实现。

使用 LangGraph ToolNode 模式进行 LLM Tool Calling。
select_endpoints_agent_node 作为 LLM 调用节点，配合 ToolNode 在图中形成循环。
"""

import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.llm.llm_client import get_chat_model
from src.core.logging import get_logger
from src.graph.state import AgentState
from src.graph.tools.db_tools import search_project, get_project_endpoints
from src.prompts.builders.select_endpoints_builder import SelectEndpointsBuilder

logger = get_logger(__name__)

AVAILABLE_TOOLS = [search_project, get_project_endpoints]


def select_endpoints_agent_node(state: AgentState) -> dict:
    """接口挑选 Agent 节点。

    将用户请求和系统提示词组装为 messages，调用绑定了工具的 LLM。
    LLM 可能返回 tool_calls（由 ToolNode 处理）或最终文本答案。

    Args:
        state: 当前 AgentState（含 messages）

    Returns:
        部分状态更新，包含新的 messages
    """
    logger.info("进入接口挑选 Agent 节点")

    model = get_chat_model()
    model_with_tools = model.bind_tools(AVAILABLE_TOOLS)

    if not state.get("messages"):
        builder = SelectEndpointsBuilder()
        messages_dicts = builder.build_messages(state["raw_input"])
        messages = [
            SystemMessage(content=messages_dicts[0]["content"]),
            HumanMessage(content=messages_dicts[1]["content"]),
        ]
    else:
        messages = state["messages"]

    response = model_with_tools.invoke(messages)
    return {"messages": [response]}


def parse_endpoints_result_node(state: AgentState) -> dict:
    """从 Agent 最终响应中提取选中的接口信息。

    Args:
        state: 当前 AgentState

    Returns:
        部分状态更新，包含 selected_endpoints
    """
    logger.info("解析接口挑选结果")

    messages = state.get("messages", [])
    if not messages:
        logger.warning("无消息可解析")
        return {"selected_endpoints": []}

    last_message = messages[-1]
    final_content = last_message.content if hasattr(last_message, "content") else ""

    if not final_content:
        logger.warning("最终消息内容为空")
        return {"selected_endpoints": []}

    logger.info(f"LLM 最终输出: {final_content[:500]}")
    selected = _parse_selected_endpoints(final_content)
    logger.info(f"选中 {len(selected)} 个接口")
    return {"selected_endpoints": selected}


def _parse_selected_endpoints(response: str) -> List[Dict[str, Any]]:
    """从 LLM 最终响应中解析选中的接口信息。

    Args:
        response: LLM 最终输出文本

    Returns:
        选中的接口列表
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

    return [
        {
            "endpoint_id": eid,
            "project_id": project_id,
            "project_name": project_name,
            "reason": reason,
        }
        for eid in endpoint_ids
    ]
