"""结束和错误处理节点。"""

from src.core.logging import get_logger
from src.graph.state import AgentState

logger = get_logger(__name__)


def end_node(state: AgentState) -> dict:
    """结束节点：输出统计信息。"""
    logger.info("工作流完成", node="end")

    return {"current_step": "completed"}
