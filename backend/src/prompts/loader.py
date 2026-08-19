"""
YAML Prompt 加载与渲染模块。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from jinja2 import Template


class PromptLoader:
    """负责加载与渲染 YAML Prompt 模板。"""

    def __init__(self, templates_dir: Path | None = None) -> None:
        if templates_dir is None:
            templates_dir = Path(__file__).resolve().parent / "templates"
        self.templates_dir = Path(templates_dir)

    def load_yaml(self, template_name: str) -> dict[str, Any]:
        """读取并解析 YAML 文件。"""
        file_path = self.templates_dir / template_name
        with file_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def render(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
        prompt_key: str = "prompt",
    ) -> str:
        """
        渲染指定 YAML 模板。

        Args:
            template_name: 模板文件名。
            context: Jinja2 上下文变量。
            prompt_key: YAML 中的提示词字段名。
        """
        data = self.load_yaml(template_name)
        prompt_template = data.get(prompt_key, "")
        if not context:
            return prompt_template
        return Template(prompt_template).render(**context)

    def load_simple_prompt_sync(self, template_name: str, prompt_key: str = "prompt") -> str:
        """同步加载简单 prompt。"""
        return self.render(template_name=template_name, context=None, prompt_key=prompt_key)


_loader = PromptLoader()


def get_loader() -> PromptLoader:
    """获取全局单例 PromptLoader。"""
    return _loader
