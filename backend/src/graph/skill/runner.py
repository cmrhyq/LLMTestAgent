"""SkillRunner：调用 LLM → 解析 → 校验 → 重试/降级的闭环执行器。

与直接调 ``llm_client.chat`` 的区别：
- 按 skill 的 error_handling 处置解析失败/校验失败/空结果
- 重试时把结构化错误注入 feedback 消息，引导模型修正
- 未声明 validation 时行为与现状完全一致（解析成功即返回）
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.core.logging import get_logger
from src.graph.skill.base import Skill
from src.graph.skill.validators import ValidationError
from src.utils.json_utils import _extract_json_str, robust_json_loads

logger = get_logger(__name__)

# 默认解析函数：返回 (data, ok)，ok=False 表示解析失败
ParseFunc = Callable[[str], tuple[Any, bool]]


def parse_full_json(response: str) -> tuple[Any, bool]:
    """从 LLM 响应中解析完整 JSON 对象。

    Returns:
        (data, ok)：ok=False 表示未找到 JSON 或解析失败（与
        parse_llm_json_response 静默返回 [] 不同，这里显式区分失败）。
    """
    if not response:
        return None, False
    json_str = _extract_json_str(response)
    if json_str is None:
        return None, False
    try:
        return robust_json_loads(json_str), True
    except json.JSONDecodeError as e:
        logger.error(f"解析LLM JSON响应失败: {e}", error=str(e))
        return None, False


@dataclass
class SkillResult:
    """SkillRunner 执行结果。"""

    raw_response: str
    final_data: Any
    errors: list[ValidationError] = field(default_factory=list)
    retries: int = 0


class SkillRunner:
    """技能执行器：build_messages → chat → parse → validate → retry/fallback。"""

    def __init__(
        self,
        llm_client: Any,
        skill: Skill,
        *,
        parse_func: ParseFunc | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.skill = skill
        self.parse_func = parse_func or parse_full_json

    def run(
        self,
        user_content: Any,
        *,
        context: dict | None = None,
    ) -> SkillResult:
        """执行技能并返回结果。

        Args:
            user_content: 用户输入（dict 时按 user_prompt 的 format 占位符渲染）
            context: 校验上下文（如 valid_endpoint_ids），透传给校验器

        Returns:
            SkillResult（final_data 为校验通过后的数据；失败按 error_handling 降级）
        """
        messages = self.skill.build_messages(user_content)
        response = self._chat(messages)
        retries = 0

        while True:
            data, ok = self.parse_func(response)

            if not ok:
                spec = self.skill.handling("parse_failure")
                if spec and spec.strategy == "retry_with_feedback" and retries < spec.max_retries:
                    feedback = self._build_feedback([ValidationError(None, "输出不是有效的 JSON 格式", response)], spec)
                    messages = messages + [{"role": "user", "content": feedback}]
                    response = self._chat(messages)
                    retries += 1
                    continue
                errors = [ValidationError(None, "输出不是有效的 JSON 格式", response)]
                if spec and spec.strategy == "fallback":
                    return SkillResult(response, spec.fallback_value, errors, retries)
                return SkillResult(response, None, errors, retries)

            errors = self.skill.run_validators(data, context) if self.skill.validation else []

            if errors:
                spec = self.skill.handling("validation_failure")
                if spec and spec.strategy == "retry_with_feedback" and retries < spec.max_retries:
                    feedback = self._build_feedback(errors, spec)
                    messages = messages + [{"role": "user", "content": feedback}]
                    response = self._chat(messages)
                    retries += 1
                    continue
                if spec and spec.strategy == "fallback":
                    return SkillResult(response, spec.fallback_value, errors, retries)
                return SkillResult(response, self._extract_final(data), errors, retries)

            final_data = self._extract_final(data)

            if final_data in (None, [], {}):
                spec = self.skill.handling("empty_result")
                if spec and spec.strategy == "fallback":
                    return SkillResult(response, spec.fallback_value, [], retries)

            return SkillResult(response, final_data, [], retries)

    # -----------------------------------------------------------
    # 内部工具
    # -----------------------------------------------------------

    def _chat(self, messages: list[dict[str, str]]) -> str:
        """调用 LLM。"""
        logger.debug(f"SkillRunner 调用 LLM，消息数: {len(messages)}", skill=self.skill.name, message_count=len(messages))
        return self.llm_client.chat(messages)

    def _extract_final(self, data: Any) -> Any:
        """按 validation.list_key 抽取最终数据；未声明 list_key 时原样返回。"""
        if self.skill.validation and self.skill.validation.list_key:
            if isinstance(data, dict):
                value = data.get(self.skill.validation.list_key, [])
                return value if isinstance(value, list) else []
            return []
        return data

    def _build_feedback(self, errors: list[ValidationError], spec) -> str:
        """把错误列表格式化为重试反馈消息。"""
        error_payload = json.dumps([e.to_dict() for e in errors], ensure_ascii=False)
        if spec.feedback_template:
            return spec.feedback_template.format(errors=error_payload)
        return f"上次输出不符合要求，错误如下：\n{error_payload}\n请严格按输出格式重新生成完整 JSON。"
