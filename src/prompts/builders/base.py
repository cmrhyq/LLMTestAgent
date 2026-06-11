"""Prompt 构建器基类。"""

from __future__ import annotations

from typing import Any

from ..loader import get_loader


class BasePromptBuilder:
    """所有 Prompt Builder 的基础能力。

    子类只需声明 SYSTEM_TEMPLATE 即可自动获得 build_system_prompt 能力。
    """

    SYSTEM_TEMPLATE: str = ""

    def __init__(self) -> None:
        self.loader = get_loader()

    def load_template(self, template_name: str) -> dict[str, Any]:
        return self.loader.load_yaml(template_name)

    def render(self, template_name: str, context: dict[str, Any] | None = None, prompt_key: str = "prompt") -> str:
        return self.loader.render(template_name=template_name, context=context, prompt_key=prompt_key)

    def build_system_prompt(self) -> str:
        """构建系统提示词（从 SYSTEM_TEMPLATE 加载）。"""
        return self.render(self.SYSTEM_TEMPLATE)

    def build_messages(self, user_content: Any) -> list[dict[str, str]]:
        """构建标准的 system + user 消息列表。

        子类可覆写此方法自定义 user_content 的组装逻辑。
        """
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": str(user_content)},
        ]
