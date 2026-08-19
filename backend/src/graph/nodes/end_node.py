"""结束和错误处理节点。"""

from src.core.logging import get_logger
from src.data.enum.workflow import TestStatus
from src.graph.constants import NodeName
from src.graph.state import AgentState

logger = get_logger(__name__)


def end_node(state: AgentState) -> dict:
    """结束节点：输出统计信息。"""
    logger.info("测试工作流正常完成", node=NodeName.END.value)

    return {"run_status": TestStatus.COMPLETED.value}
