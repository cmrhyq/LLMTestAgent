"""起始节点：验证输入并初始化状态。"""

from src.core.logging import get_logger
from src.graph.state import AgentState

logger = get_logger(__name__)


def start_node(state: AgentState) -> dict:
    """起始节点：验证输入并初始化状态。

    LangGraph 节点函数：
    - 接收当前状态作为参数
    - 返回需要更新的状态字段（字典）
    - 返回的字段会合并到当前状态中
    """
    logger.info("=== 开始API测试工作流 ===")
    logger.info(f"测试目标：{state.get('raw_input')}, 输入文件：{state.get('api_doc_file_path')}")

    raw_input = state.get("raw_input")
    if not raw_input:
        return {
            "current_step": "error",
            "error_message": "输入为空，无法进行工作流",
        }

    return {
        "current_step": "parse_input",
        "error_message": "",
    }
