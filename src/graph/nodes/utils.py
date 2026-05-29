"""Graph 节点公共工具函数。

提供各节点共享的数据库初始化、JSON 解析、配置读取等通用能力。
"""

import json
from typing import Any

from src.core.config import get_config
from src.core.database.connection import get_db_manager


def ensure_db() -> None:
    """确保数据库已初始化。"""
    manager = get_db_manager()
    if not manager._initialized:
        config = get_config()
        manager.initialize(
            db_url=config.database.url,
            echo=config.database.echo,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_timeout=config.database.pool_timeout,
            pool_recycle=config.database.pool_recycle,
        )


def safe_json_loads(value: str | None, default: Any) -> Any:
    """安全解析 JSON 字段。"""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def get_model_name(config) -> str:
    """获取当前使用的模型名称。"""
    provider = config.llm.provider.lower()
    if provider == "openai":
        return config.llm.openai.model
    if provider == "bedrock":
        return config.llm.bedrock.model_id
    if provider == "zhipu":
        return config.llm.zhipu.model
    if provider == "qwen":
        return config.llm.qwen.model
    return provider
