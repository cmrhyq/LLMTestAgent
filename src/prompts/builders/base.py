"""Prompt 构建器基类。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..loader import get_loader


class BasePromptBuilder:
    """所有 Prompt Builder 的基础能力。"""

    def __init__(self) -> None:
        self.loader = get_loader()

    def load_template(self, template_name: str) -> Dict[str, Any]:
        return self.loader.load_yaml(template_name)

    def render(self, template_name: str, context: Optional[Dict[str, Any]] = None, prompt_key: str = "prompt") -> str:
        return self.loader.render(template_name=template_name, context=context, prompt_key=prompt_key)

