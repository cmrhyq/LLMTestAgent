"""用例生成 Prompt Builder。"""

from __future__ import annotations

from typing import Any

from ..formatters.case_formatter import format_api_info_for_prompt
from .base import BasePromptBuilder


class CasePromptBuilder(BasePromptBuilder):
    """负责生成单接口用例生成场景的系统/用户提示词。"""

    SYSTEM_TEMPLATE = "single_case_system.yaml"
    USER_TEMPLATE = "single_case_user.yaml"

    def build_user_prompt(self, api_info: dict[str, Any], scenario_types: str) -> str:
        context = format_api_info_for_prompt(api_info)
        context["scenario_types"] = scenario_types
        template = self.render(self.USER_TEMPLATE)
        return template.format(**context)


def build_case_prompts(api_info: dict[str, Any], scenario_types: str) -> tuple[str, str]:
    """一次性返回 system/user prompt。"""
    builder = CasePromptBuilder()
    return builder.build_system_prompt(), builder.build_user_prompt(api_info, scenario_types)
