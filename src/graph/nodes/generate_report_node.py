"""报告生成节点。

根据测试结果生成测试报告。
"""

from src.core.logging import get_logger
from src.graph.state import TestGraphState

logger = get_logger(__name__)


def generate_report_node(state: TestGraphState) -> dict:
    """报告生成节点。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 report_path 字段
    """
    logger.info("进入报告生成节点")

    try:
        report_path = "a"
        logger.info(f"报告生成成功: {report_path}")
        return {"report_path": report_path}

    except Exception as e:
        error_msg = f"报告生成异常: {str(e)}"
        logger.error(error_msg)
        return {"error_message": error_msg}
