"""LLM 响应解析公共工具函数。

提供各节点共享的数据库初始化、JSON 解析、配置读取等通用能力。
LLM 输出的 JSON 解析统一通过 robust_json_loads 进行兜底修复。
"""

import json
import re
from typing import Any

from json_repair import repair_json

from src.core.config import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger

logger = get_logger(__name__)


def safe_json_loads(value: str | None, default: Any) -> Any:
    """安全解析 JSON 字段，失败时使用 json_repair 修复。"""
    if not value:
        return default
    try:
        return robust_json_loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def robust_json_loads(text: str) -> Any:
    """先尝试标准 json.loads，失败后使用 json_repair 修复再解析。

    Args:
        text: 待解析的 JSON 字符串

    Returns:
        解析后的 Python 对象

    Raises:
        json.JSONDecodeError: 标准解析和修复均失败时抛出
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("标准JSON解析失败，尝试修复", raw_length=len(text) if text else 0)
        try:
            repaired = repair_json(text, return_objects=True)
            logger.info("JSON修复成功")
            return repaired
        except Exception as e:
            logger.error("JSON修复也失败", error=str(e))
            raise json.JSONDecodeError(f"repair also failed: {e}", text or "", 0) from e


def parse_llm_json_response(
    response: str,
    *,
    list_key: str = "test_cases",
    sort_key: str | None = None,
) -> list[dict[str, Any]]:
    """从 LLM 响应文本中解析 JSON 列表。

    支持 markdown code block 包裹和纯 JSON 文本。
    若解析结果为 dict，则取 list_key 对应的子列表；
    若为 list 则直接使用。可选按 sort_key 排序。

    解析失败时自动使用 json_repair 进行修复。
    """
    response = response.strip()

    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
    else:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start == -1 or json_end <= 0:
            logger.warning("LLM响应中未找到JSON内容")
            return []
        json_str = response[json_start:json_end]

    try:
        data = robust_json_loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"解析LLM JSON响应失败: {e}", error=str(e))
        return []

    if isinstance(data, dict):
        cases = data.get(list_key, [])
        if not isinstance(cases, list):
            return []
    elif isinstance(data, list):
        cases = data
    else:
        return []

    if sort_key:
        cases.sort(key=lambda c: c.get(sort_key, 0))

    return cases


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
