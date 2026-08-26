"""请求域 LangChain Tool：发送 HTTP 请求。

包装 HttpRequest 类为原子 Tool，供 LLM 直接发请求并取回响应摘要。
"""

import json
from typing import Any

from langchain_core.tools import tool

from src.core.logging import get_logger
from src.graph.tools._common import as_object
from src.utils.http.request import HttpRequest, split_url
from src.utils.json_utils import safe_json_loads

logger = get_logger(__name__)


@tool
def send_request(
    url: str,
    method: str = "GET",
    headers: str = "{}",
    body: str = "{}",
    params: str = "{}",
    timeout: int = 30,
) -> str:
    """发送 HTTP 请求并返回响应摘要（状态码、响应头、响应体、耗时）。

    Args:
        url: 完整请求 URL（含协议与域名）
        method: HTTP 方法，GET/POST/PUT/DELETE/PATCH，默认 GET
        headers: 请求头 JSON 字符串，如 {"Authorization": "Bearer xxx"}，默认 {}
        body: 请求体 JSON 字符串（POST/PUT/PATCH 时使用），默认 {}
        params: 查询参数 JSON 字符串，如 {"page": 1}，默认 {}
        timeout: 连接与读取超时秒数，默认 30

    Returns:
        JSON 字符串: {"status_code": int, "response_time_ms": float,
                       "headers": {...}, "body": <响应体>}
    """
    http_client: HttpRequest | None = None
    try:
        base_url, endpoint = split_url(url)
        headers_dict = safe_json_loads(headers, {}) or {}
        params_dict = safe_json_loads(params, {}) or {}
        body_obj = as_object(body)

        http_client = HttpRequest(base_url=base_url, connect_timeout=timeout, read_timeout=timeout, verify_ssl=True)

        method_map = {
            "GET": http_client.get,
            "POST": http_client.post,
            "PUT": http_client.put,
            "DELETE": http_client.delete,
            "PATCH": http_client.patch,
        }
        request_func = method_map.get(method.upper())
        if not request_func:
            return json.dumps({"error": f"不支持的 HTTP 方法: {method}"}, ensure_ascii=False)

        request_kwargs: dict[str, Any] = {"headers": headers_dict, "enable_retry": False}
        if params_dict:
            request_kwargs["params"] = params_dict
        if method.upper() in ("POST", "PUT", "PATCH") and body_obj is not None:
            request_kwargs["json"] = body_obj

        response = request_func(endpoint, **request_kwargs)
        if response is None:
            return json.dumps({"error": "请求失败，无响应"}, ensure_ascii=False)

        try:
            resp_body = response.json()
        except Exception:
            resp_body = response.text[:10000]

        return json.dumps(
            {
                "status_code": response.status_code,
                "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                "headers": {k: v for k, v in response.headers.items() if k.lower() != "set-cookie"},
                "body": resp_body,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as e:
        logger.error(f"HTTP 请求失败: {e}", url=url, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if http_client is not None:
            http_client.close()
