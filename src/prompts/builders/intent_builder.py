"""意图分类 Prompt Builder。"""

from __future__ import annotations

from typing import Dict, List

from .base import BasePromptBuilder


class IntentPromptBuilder(BasePromptBuilder):
    """负责生成意图分类场景的系统提示词和消息列表。"""

    SYSTEM_TEMPLATE = "intent_system.yaml"

    def build_system_prompt(self) -> str:
        return self.render(self.SYSTEM_TEMPLATE)

    def build_messages(self, user_input: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_input},
        ]
