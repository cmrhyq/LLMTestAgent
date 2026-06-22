"""缓存参数处理器模块。

负责测试用例执行过程中的参数依赖管理:
- inject: 从 DataCache 中取值注入到请求的 headers/body/params
- extract: 从 HTTP 响应中提取值存入 DataCache

cache_rules JSON 格式约定:
{
  "inject": [
    {"cache_key": "auth_token", "target": "headers.Authorization", "template": "Bearer {value}"}
  ],
  "extract": [
    {"source_path": "$.data.token", "cache_key": "auth_token"}
  ]
}
"""

import copy
import re
from typing import Any

from src.core.cache.data_cache import DataCache
from src.core.logging import get_logger

logger = get_logger(__name__)


class CacheResolver:
    """缓存参数注入与提取处理器。"""

    def __init__(self, cache: DataCache | None = None) -> None:
        self.cache = cache or DataCache.get_instance()

    def inject(
        self,
        headers: dict[str, str],
        body: dict[str, Any] | None,
        params: dict[str, Any] | None,
        cache_rules: dict[str, Any] | None,
    ) -> tuple[dict[str, str], dict[str, Any] | None, dict[str, Any] | None]:
        """将缓存中的值注入到请求参数中。

        Args:
            headers: 请求头（会被修改副本）
            body: 请求体（会被修改副本）
            params: 查询参数（会被修改副本）
            cache_rules: 缓存规则字典

        Returns:
            (headers, body, params) 注入后的参数副本
        """
        headers = copy.deepcopy(headers) if headers else {}
        body = copy.deepcopy(body) if body else None
        params = copy.deepcopy(params) if params else None

        if not cache_rules:
            return headers, body, params

        inject_rules = cache_rules.get("inject", [])
        if not inject_rules:
            return headers, body, params

        for rule in inject_rules:
            cache_key = rule.get("cache_key", "")
            target = rule.get("target", "")
            template = rule.get("template", "{value}")

            if not cache_key or not target:
                continue

            if not self.cache.has(cache_key):
                logger.debug(f"缓存键不存在，跳过注入: {cache_key}", cache_key=cache_key)
                continue

            raw_value = self.cache.get(cache_key)
            value = template.replace("{value}", str(raw_value)) if template else str(raw_value)

            headers, body, params = self._set_target_value(headers, body, params, target, value)
            logger.debug(f"缓存注入成功: {cache_key} -> {target}", cache_key=cache_key, target=target)

        return headers, body, params

    def extract(
        self,
        response_body: Any,
        cache_rules: dict[str, Any] | None,
    ) -> None:
        """从响应体中提取值并存入缓存。

        Args:
            response_body: HTTP 响应体（已解析的 dict/list）
            cache_rules: 缓存规则字典
        """
        if not cache_rules:
            return

        extract_rules = cache_rules.get("extract", [])
        if not extract_rules:
            return

        for rule in extract_rules:
            source_path = rule.get("source_path", "")
            cache_key = rule.get("cache_key", "")

            if not source_path or not cache_key:
                continue

            value = self._extract_by_jsonpath(response_body, source_path)
            if value is not None:
                self.cache.set(cache_key, value)
                logger.debug(
                    f"缓存提取成功: {cache_key}={str(value)[:100]}", cache_key=cache_key, value_preview=str(value)[:100]
                )
            else:
                logger.warning(
                    f"缓存提取失败，路径无匹配: path={source_path}, key={cache_key}",
                    source_path=source_path,
                    cache_key=cache_key,
                )

    def has_unresolved_dependencies(self, cache_rules: dict[str, Any] | None) -> bool:
        """检查是否存在未满足的缓存依赖。

        Args:
            cache_rules: 缓存规则字典

        Returns:
            True 表示有依赖的 cache_key 尚不存在于缓存中
        """
        if not cache_rules:
            return False

        inject_rules = cache_rules.get("inject", [])
        for rule in inject_rules:
            cache_key = rule.get("cache_key", "")
            if cache_key and not self.cache.has(cache_key):
                return True
        return False

    def _set_target_value(
        self,
        headers: dict[str, str],
        body: dict[str, Any] | None,
        params: dict[str, Any] | None,
        target: str,
        value: Any,
    ) -> tuple[dict[str, str], dict[str, Any] | None, dict[str, Any] | None]:
        """将值设置到指定的 target 路径中。

        target 格式: "headers.Authorization" / "body.data.token" / "params.page"
        """
        parts = target.split(".", 1)
        if len(parts) < 2:
            return headers, body, params

        scope = parts[0]
        path = parts[1]

        if scope == "headers":
            headers[path] = str(value)
        elif scope == "body":
            if body is None:
                body = {}
            self._set_nested_value(body, path, value)
        elif scope == "params":
            if params is None:
                params = {}
            self._set_nested_value(params, path, value)

        return headers, body, params

    @staticmethod
    def _set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套字典中的值。

        path 支持点分隔，如 "data.user.id" 将设置 data["data"]["user"]["id"]
        """
        keys = path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    @staticmethod
    def _extract_by_jsonpath(data: Any, path: str) -> Any:
        """简易 JSONPath 提取（支持 $.a.b.c 和 $.a[0].b 格式）。"""
        if data is None:
            return None

        if path == "$":
            return data

        stripped = path.lstrip("$").lstrip(".")
        if not stripped:
            return data

        tokens: list[str] = []
        for segment in stripped.split("."):
            if not segment:
                continue
            bracket_match = re.match(r"^(\w+)\[(\d+)\]$", segment)
            if bracket_match:
                tokens.append(bracket_match.group(1))
                tokens.append(bracket_match.group(2))
            else:
                tokens.append(segment)

        current = data
        for token in tokens:
            if current is None:
                return None
            if token.isdigit():
                idx = int(token)
                if isinstance(current, list) and idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(token)
            else:
                return None

        return current
