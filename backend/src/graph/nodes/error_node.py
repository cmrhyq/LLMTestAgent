"""错误处理节点：记录错误信息。"""

from src.core.logging import get_logger
from src.data.enum.workflow import TestStatus
from src.graph.constants import NodeName
from src.graph.state import AgentState

logger = get_logger(__name__)


def error_node(state: AgentState) -> dict:
    """错误处理节点：记录错误信息。"""
    error_msg = state.get("error_message", "未知错误")
    logger.error(f"工作流出错: {error_msg}", node=NodeName.ERROR.value, error=error_msg)

    return {"run_status": TestStatus.FAILED.value}
