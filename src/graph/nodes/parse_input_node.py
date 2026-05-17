"""意图解析节点。

调用 LLM 判断用户意图：run_test 或 parse_openapi，
并在 run_test 场景下区分测试模式：single（单接口）或 flow（业务流程）。
"""

import json
import re
from typing import Dict

from src.core.llm.llm_client import get_llm_client
from src.core.logging import get_logger
from src.graph.state import AgentState
from src.prompts.builders.intent_builder import IntentPromptBuilder

logger = get_logger(__name__)

_VALID_INTENTS = ("run_test", "parse_openapi")
_VALID_TEST_MODES = ("single", "flow")


def parse_input_node(state: AgentState) -> dict:
    """意图解析节点：调用 LLM 识别用户意图和测试模式。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 user_intent 和 test_mode 字段
    """
    logger.info("节点进入, node: parse_input", node="parse_input")

    try:
        builder = IntentPromptBuilder()
        messages = builder.build_messages(state["raw_input"])

        llm_client = get_llm_client()
        response = llm_client.chat(messages)
        logger.debug(f"LLM意图分类响应, response: {response}", response=response)

        result = _extract_classification(response)
        logger.info(f"意图识别完成, intent: {result['intent']}, test_mode: {result['test_mode']}", intent=result["intent"], test_mode=result["test_mode"])
        return {
            "user_intent": result["intent"],
            "test_mode": result["test_mode"]
        }

    except Exception as e:
        error_msg = f"输入解析异常: {str(e)}"
        logger.error(f"意图解析失败，使用默认值, error: {e}, default_intent: run_test, default_mode: single", error=str(e), default_intent="run_test", default_mode="single")
        return {
            "user_intent": "run_test",
            "test_mode": "single", "error_message": error_msg
        }


def _extract_classification(response: str) -> Dict[str, str]:
    """从 LLM 响应中提取意图和测试模式。

    优先使用 JSON 解析，失败时使用正则匹配作为后备。

    Args:
        response: LLM 原始响应文本

    Returns:
        包含 intent 和 test_mode 的字典
    """
    try:
        data = json.loads(response.strip())
        intent = data.get("intent", "")
        test_mode = data.get("test_mode", "single")
        if intent in _VALID_INTENTS:
            return {
                "intent": intent,
                "test_mode": test_mode if test_mode in _VALID_TEST_MODES else "single",
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    intent_match = re.search(r'"intent"\s*:\s*"(run_test|parse_openapi)"', response)
    mode_match = re.search(r'"test_mode"\s*:\s*"(single|flow)"', response)

    return {
        "intent": intent_match.group(1) if intent_match else "run_test",
        "test_mode": mode_match.group(1) if mode_match else "single",
    }
