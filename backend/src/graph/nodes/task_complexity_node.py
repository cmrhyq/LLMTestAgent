"""
任务复杂度分级节点

分析用户输入的复杂度，选择合适的 AI 模型进行后续处理。
可用模型：
  - us.anthropic.claude-opus-4-6-v1（旗舰级）
  - us.anthropic.claude-sonnet-4-6（均衡级）
  - us.anthropic.claude-haiku-4-5-20251001-v1:0（轻量级）
"""

import json
import re

from src.core.llm.llm_client import get_llm_client
from src.core.logging import get_logger
from src.graph.state import AgentState
from src.prompts.builders.task_complexity_builder import TaskComplexityBuilder

logger = get_logger(__name__)

# 模型 ID 映射
MODEL_MAP = {
    "simple": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "moderate": "us.anthropic.claude-sonnet-4-6",
    "complex": "us.anthropic.claude-opus-4-6-v1",
}

# 默认模型（解析失败时使用）
DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-6"
DEFAULT_LEVEL = "moderate"


def task_complexity_node(state: AgentState) -> dict:
    """任务复杂度分级节点：分析用户输入复杂度并选择模型。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新，包含 selected_model 和 complexity_level 字段
    """
    raw_input = state.get("raw_input", "")
    logger.info(
        f"进入任务复杂度分级节点，用户指令: {raw_input[:80]}",
        node="task_complexity",
        raw_input=raw_input,
    )

    try:
        builder = TaskComplexityBuilder()
        messages = builder.build_messages(raw_input)

        llm_client = get_llm_client()
        response = llm_client.chat(messages)
        logger.debug(
            f"复杂度分级原始响应: {response[:300]}",
            node="task_complexity",
            response_length=len(response),
        )

        result = _extract_complexity_result(response)
        logger.info(
            f"复杂度分级完成，等级: {result['complexity_level']}，模型: {result['selected_model']}",
            node="task_complexity",
            complexity_level=result["complexity_level"],
            selected_model=result["selected_model"],
            weighted_score=result.get("weighted_score"),
        )

        return {
            "selected_model": result["selected_model"],
            "complexity_level": result["complexity_level"],
            "complexity_scores": result.get("scores", {}),
            "complexity_rationale": result.get("rationale", ""),
        }

    except Exception as e:
        error_msg = f"复杂度分级异常: {str(e)}"
        logger.error(
            f"复杂度分级失败，使用默认模型({DEFAULT_MODEL}): {e}",
            node="task_complexity",
            error=str(e),
            default_model=DEFAULT_MODEL,
        )
        return {
            "selected_model": DEFAULT_MODEL,
            "complexity_level": DEFAULT_LEVEL,
            "complexity_scores": {},
            "complexity_rationale": error_msg,
        }


def _extract_complexity_result(response: str) -> dict:
    """从 LLM 响应中提取复杂度分级结果。

    优先使用 JSON 解析，失败时使用正则匹配作为后备。

    Args:
        response: LLM 原始响应文本

    Returns:
        包含 complexity_level、selected_model 等字段的字典
    """
    # 尝试提取 JSON 块（可能包含 ```json ... ``` 包裹）
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    json_str = json_match.group(1) if json_match else response.strip()

    try:
        data = json.loads(json_str)
        complexity_level = data.get("complexity_level", "")
        selected_model = data.get("selected_model", "")

        # 验证 complexity_level
        if complexity_level not in MODEL_MAP:
            complexity_level = DEFAULT_LEVEL

        # 验证 selected_model（如果 LLM 返回的 model 不合法，用 level 映射）
        valid_models = set(MODEL_MAP.values())
        if selected_model not in valid_models:
            selected_model = MODEL_MAP[complexity_level]

        return {
            "complexity_level": complexity_level,
            "selected_model": selected_model,
            "scores": data.get("scores", {}),
            "weighted_score": data.get("weighted_score", 0.0),
            "rationale": data.get("rationale", ""),
        }
    except (json.JSONDecodeError, AttributeError):
        pass

    # 正则后备方案
    level_match = re.search(r'"complexity_level"\s*:\s*"(simple|moderate|complex)"', response)
    model_match = re.search(r'"selected_model"\s*:\s*"([^"]+)"', response)

    complexity_level = level_match.group(1) if level_match else DEFAULT_LEVEL
    selected_model = model_match.group(1) if model_match else MODEL_MAP[complexity_level]

    # 再次验证 model
    valid_models = set(MODEL_MAP.values())
    if selected_model not in valid_models:
        selected_model = MODEL_MAP[complexity_level]

    return {
        "complexity_level": complexity_level,
        "selected_model": selected_model,
        "scores": {},
        "weighted_score": 0.0,
        "rationale": "",
    }
