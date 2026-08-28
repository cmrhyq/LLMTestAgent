"""执行域 LangChain Tools：断言评估、JSONPath 提取、缓存读写。

将 AssertionEngine、jsonpath、DataCache 等底层能力包装为原子 Tool，
供 LLM 通过 function calling 直接调用（如生成用例后即时自验断言）。

设计原则:
- Tool = 原子能力（"手"）：无编排、入参出参明确、可跨任务复用
- 输入输出均为 JSON 字符串 / 基本类型，便于 LLM 传参
"""

import json

from langchain_core.tools import tool

from src.core.cache.cache_manager import CacheManager
from src.core.logging import get_logger
from src.graph.executor.assertion_engine import AssertionEngine
from src.graph.executor.jsonpath import extract_jsonpath as _extract_jsonpath_impl
from src.graph.tools._common import as_object

logger = get_logger(__name__)

# 单例断言引擎（无状态，可复用）
_assertion_engine = AssertionEngine()


@tool
def evaluate_assertions(
    rules: list[str],
    response_body: str,
    status_code: int = 0,
    response_time: float = 0.0,
) -> str:
    """评估接口断言规则，返回每条规则的通过情况。

    用于生成测试用例后即时自验断言是否可执行、结果是否符合预期。
    支持语法:
    - $.code == 200           JSONPath 等值比较
    - $.data.token exists     字段存在性检查
    - $.message contains "x"  包含子串
    - status_code == 200      HTTP 状态码
    - response_time < 3000    响应时间(ms)

    Args:
        rules: 断言规则字符串列表，如 ["$.code == 200", "$.data.token exists"]
        response_body: HTTP 响应体（JSON 字符串；非 JSON 文本也可直接传入）
        status_code: HTTP 状态码，默认 0
        response_time: 响应耗时（毫秒），默认 0

    Returns:
        JSON 字符串: {"all_passed": bool, "details": [{rule, passed, actual, expected, operator}]}
    """
    try:
        body = as_object(response_body)
        all_passed, details = _assertion_engine.evaluate_all(rules, body, status_code, response_time)
        return json.dumps({"all_passed": all_passed, "details": details}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"断言评估失败: {e}", error=str(e))
        return json.dumps({"all_passed": False, "error": str(e)}, ensure_ascii=False)


@tool
def extract_jsonpath(data: str, path: str) -> str:
    """按 JSONPath 从 JSON 数据中提取值（支持 $.a.b.c 与 $.a[0].b）。

    Args:
        data: JSON 字符串（待提取的数据）
        path: JSONPath 表达式，如 "$.data.token" 或 "$.items[0].id"

    Returns:
        提取到的值（JSON 编码）；未命中返回 null
    """
    obj = as_object(data)
    result = _extract_jsonpath_impl(obj, path)
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def resolve_cache(cache_key: str) -> str:
    """从执行缓存中按 key 读取之前提取/保存的值。

    Args:
        cache_key: 缓存键名

    Returns:
        缓存值（JSON 编码）；键不存在返回 null
    """
    cache = CacheManager.get_instance()
    if not cache.has(cache_key):
        return "null"
    value = cache.get(cache_key)
    return json.dumps(value, ensure_ascii=False, default=str)


@tool
def extract_cache(cache_key: str, source_path: str, response_body: str) -> str:
    """从响应体中按 JSONPath 提取值并存入执行缓存，供后续用例依赖注入使用。

    Args:
        cache_key: 缓存键名（后续通过 resolve_cache / cache 注入规则引用同一 key）
        source_path: 取值路径，如 "$.data.token"
        response_body: HTTP 响应体 JSON 字符串

    Returns:
        提取到的值（JSON 编码）；未命中返回 null
    """
    try:
        body = as_object(response_body)
        value = _extract_jsonpath_impl(body, source_path)
        CacheManager.get_instance().set(cache_key, value)
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"缓存提取失败: {e}", cache_key=cache_key, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)
