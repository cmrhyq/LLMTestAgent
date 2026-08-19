"""LLM 相关工具：模型名解析。

历史上本模块聚合了 JSON 解析与数据库初始化逻辑，现已分别拆分到
``src.utils.json_utils`` 与 ``src.utils.db_bootstrap``。为兼容既有引用，
此处继续 re-export 这些函数。
"""

from src.core.config import AppConfig
from src.utils.db_bootstrap import ensure_db
from src.utils.json_utils import (
    parse_llm_json_object,
    parse_llm_json_response,
    robust_json_loads,
    safe_json_loads,
)

__all__ = [
    "ensure_db",
    "get_model_name",
    "parse_llm_json_object",
    "parse_llm_json_response",
    "robust_json_loads",
    "safe_json_loads",
]


def get_model_name(config: AppConfig) -> str:
    """根据 provider 返回当前使用的模型名称。"""
    provider = config.llm.provider.lower()
    if provider == "openai":
        return config.llm.openai.model
    if provider == "bedrock":
        return config.llm.bedrock.model_id
    if provider == "zhipu":
        return config.llm.zhipu.model
    if provider == "qwen":
        return config.llm.qwen.model
    if provider == "deepseek":
        return config.llm.deepseek.model
    return provider
