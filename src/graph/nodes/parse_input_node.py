"""意图解析节点。

调用 LLM 判断用户意图：run_test 或 parse_openapi。
"""

import json
import re

from src.core.llm.llm_client import get_llm_client
from src.core.logging import get_logger
from src.graph.state import TestGraphState
from src.prompts.builders.intent_builder import IntentPromptBuilder

logger = get_logger(__name__)

_VALID_INTENTS = ("run_test", "parse_openapi")


def parse_input_node(state: TestGraphState) -> dict:
    """意图解析节点：调用 LLM 识别用户意图。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 user_intent 字段
    """
    logger.info("进入意图解析节点")

    try:
        builder = IntentPromptBuilder()
        messages = builder.build_messages(state["raw_input"])

        llm_client = get_llm_client()
        response = llm_client.chat(messages)
        logger.info(f"LLM 意图分类响应: {response}")

        intent = _extract_intent(response)
        logger.info(f"识别到用户意图: {intent}")
        return {"user_intent": intent}

    except Exception as e:
        error_msg = f"输入解析异常: {str(e)}"
        logger.error(f"{error_msg}，使用默认意图: run_test")
        return {"user_intent": "run_test", "error_message": error_msg}


def _extract_intent(response: str) -> str:
    """从 LLM 响应中提取意图。

    优先使用 JSON 解析，失败时使用正则匹配作为后备。

    Args:
        response: LLM 原始响应文本

    Returns:
        意图标识 ("run_test" 或 "parse_openapi")
    """
    try:
        data = json.loads(response.strip())
        intent = data.get("intent", "")
        if intent in _VALID_INTENTS:
            return intent
    except (json.JSONDecodeError, AttributeError):
        pass

    match = re.search(r'"intent"\s*:\s*"(run_test|parse_openapi)"', response)
    if match:
        return match.group(1)

    return "run_test"
