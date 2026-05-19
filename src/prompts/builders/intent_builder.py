"""意图分类 Prompt Builder。"""

from __future__ import annotations

from .base import BasePromptBuilder


class IntentPromptBuilder(BasePromptBuilder):
    """负责生成意图分类场景的系统提示词和消息列表。"""

    SYSTEM_TEMPLATE = "intent_system.yaml"
