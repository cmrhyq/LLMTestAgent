"""用例生成 Prompt 的格式化工具。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def format_scenario_types(scenarios: Any) -> str:
    """
    将场景配置转换为用户提示词中的列表文本。

    支持对象属性访问（如 pydantic model）和 dict 两种输入。
    """

    def _enabled(name: str) -> bool:
        if isinstance(scenarios, Mapping):
            return bool(scenarios.get(name, False))
        return bool(getattr(scenarios, name, False))

    lines = []
    if _enabled("normal"):
        lines.append("- 正常场景 (normal)")
    if _enabled("param_missing"):
        lines.append("- 参数缺失场景 (param_missing)")
    if _enabled("param_type_error"):
        lines.append("- 参数类型错误场景 (param_type_error)")
    if _enabled("boundary_value"):
        lines.append("- 边界值场景 (boundary_value)")
    if _enabled("permission_error"):
        lines.append("- 权限异常场景 (permission_error)")
    return "\n".join(lines)


def format_api_info_for_prompt(api_info: dict[str, Any]) -> dict[str, Any]:
    """规范化 API 信息，供 Jinja2 模板渲染。"""
    return {
        "name": api_info.get("name", ""),
        "url": api_info.get("url", ""),
        "method": str(api_info.get("method", "")),
        "headers": json.dumps(api_info.get("headers", {}), ensure_ascii=False, indent=2),
        "body": (
            json.dumps(api_info.get("body"), ensure_ascii=False, indent=2) if api_info.get("body") is not None else "无"
        ),
        "params": (
            json.dumps(api_info.get("params"), ensure_ascii=False, indent=2)
            if api_info.get("params") is not None
            else "无"
        ),
        "assert_rules": json.dumps(api_info.get("assert_rules", []), ensure_ascii=False),
        "priority": str(api_info.get("priority", "P1")),
        "description": api_info.get("description") or "无",
    }
