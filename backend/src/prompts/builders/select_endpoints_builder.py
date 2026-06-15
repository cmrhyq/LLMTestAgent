"""接口挑选 Prompt Builder。"""

from __future__ import annotations

from .base import BasePromptBuilder


class SelectEndpointsBuilder(BasePromptBuilder):
    """负责生成接口挑选场景的系统提示词和消息列表。"""

    SYSTEM_TEMPLATE = "select_endpoints_system.yaml"

    def build_messages(self, user_input: str) -> list[dict[str, str]]:
        return super().build_messages(f"测试目标：{user_input}")
