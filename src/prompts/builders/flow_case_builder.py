"""流程用例生成 Prompt Builder。"""

from __future__ import annotations

import json
from typing import Any

from .base import BasePromptBuilder


class FlowCasePromptBuilder(BasePromptBuilder):
    """负责生成流程测试用例场景的系统/用户提示词。"""

    SYSTEM_TEMPLATE = "flow_case_system.yaml"
    USER_TEMPLATE = "flow_case_user.yaml"

    def build_user_prompt(self, endpoints_info: list[dict[str, Any]]) -> str:
        formatted = json.dumps(endpoints_info, ensure_ascii=False, indent=2)
        template = self.render(self.USER_TEMPLATE)
        return template.format(endpoints_info=formatted)

    def build_messages(self, endpoints_info: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": self.build_user_prompt(endpoints_info)},
        ]


def build_flow_case_prompts(endpoints_info: list[dict[str, Any]]) -> tuple[str, str]:
    """一次性返回 system/user prompt。"""
    builder = FlowCasePromptBuilder()
    return builder.build_system_prompt(), builder.build_user_prompt(endpoints_info)
