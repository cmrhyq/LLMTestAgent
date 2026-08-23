from src.core.logging import get_logger
from src.graph import AgentState
from src.graph.constants import NodeName

logger = get_logger(__name__)


def answer_question_node(state: AgentState) -> dict:
    """回答问题节点：调用LLM回答用户问题。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 user_intent 和 test_mode 字段
    """
    logger.info(
        f"进入回答问题节点，用户指令: {state['raw_input'][:80]}", node="ask", raw_input=state["raw_input"]
    )
    try:

        return {"answer_content": "", "next_node": NodeName.END.value}
    except Exception as e:
        logger.error(
            f"Answer Question Node异常: {e}",
            node=NodeName.ANSWER_QUESTION.value,
            error=str(e),
            default_intent="ask",
            default_mode="single",
        )
        return {"next_node": NodeName.ERROR.value, "error_message": f"Answer Question Node异常: {str(e)}"}
