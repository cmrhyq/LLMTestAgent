"""
用户输入安全审计节点

审计用户的输入，判断用户的prompt是否涉及安全问题以及是否不是API测试的内容
"""

from src import get_llm_client
from src.core.logging import get_logger
from src.graph.state import AgentState
from src.prompts.builders.system_safety import SystemSafetyBuilder

logger = get_logger(__name__)


def security_audit_node(state: AgentState) -> dict:
    """用户输入安全审计节点

    Args:
        state: 当前工作流状态

    Returns:
        是否通过审计以及审计结果
    """
    logger.info(
        f"进入Prompt安全审计节点，用户指令: {state['raw_input'][:80]}", node="parse_input", raw_input=state["raw_input"]
    )

    try:
        builder = SystemSafetyBuilder()
        messages = builder.build_messages(state["raw_input"])

        llm_client = get_llm_client()
        response = llm_client.chat(messages)

        logger.info(f"Prompt安全审计响应：: {response}", node="security_audit")
        return {"current_step": "", "audit_result": response}
    except Exception as e:
        error_msg = f"Prompt安全审计异常：{str(e)}"
        logger.error(f"Prompt安全审计失败，拦截此次会话请求：{e}", node="security_audit_", error=str(e))
        return {"current_step": "error", "error_message": error_msg}
