"""Prompts 统一导出。"""

from .loader import get_loader
from .builders.case_builder import CasePromptBuilder, build_case_prompts
from .formatters.case_formatter import format_api_info_for_prompt, format_scenario_types

_loader = get_loader()

# 向后兼容：提供常量接口（由 YAML 加载）
CASE_GENERATION_SYSTEM_PROMPT = _loader.load_simple_prompt_sync("case_system.yaml")
CASE_GENERATION_USER_PROMPT_TEMPLATE = _loader.load_simple_prompt_sync("case_user.yaml")

__all__ = [
    "CASE_GENERATION_SYSTEM_PROMPT",
    "CASE_GENERATION_USER_PROMPT_TEMPLATE",
    "CasePromptBuilder",
    "build_case_prompts",
    "format_api_info_for_prompt",
    "format_scenario_types",
]

