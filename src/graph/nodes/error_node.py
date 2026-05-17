from src.core.logging import get_logger
from src.graph.state import AgentState

logger = get_logger(__name__)


def error_node(state: AgentState) -> dict:
    """错误处理节点：记录错误信息。"""
    error_msg = state.get("error_message", "未知错误")
    logger.error(f"工作流出错, node: error, error: {error_msg}", node="error", error=error_msg)

    return {"current_step": "failed"}