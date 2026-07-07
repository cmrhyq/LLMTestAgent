"""任务复杂度分级 Prompt Builder。

根据用户输入评估任务复杂度，选择合适的 AI 模型。
"""

from __future__ import annotations

from .base import BasePromptBuilder


class TaskComplexityBuilder(BasePromptBuilder):
    """负责生成任务复杂度分级场景的系统提示词和消息列表。"""

    SYSTEM_TEMPLATE = "task_complexity_system.yaml"

    def build_messages(self, user_input: str) -> list[dict[str, str]]:
        return super().build_messages(f"用户输入：{user_input}")
