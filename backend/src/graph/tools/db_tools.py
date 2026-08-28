"""数据库查询 LangChain Tools。

提供 search_space 和 get_space_endpoints 两个工具，
供 LLM 通过 function calling 自动调用。
"""

import json

from langchain_core.tools import tool

from src.core.database.database_manager import get_db_manager
from src.data.services import EndpointService, SpaceService
from src.core.database.database_manager import init_database_from_config


@tool
def search_space(name: str) -> str:
    """根据名称搜索空间，支持模糊匹配。返回匹配的空间列表（JSON格式），包含id、name、description字段。"""
    init_database_from_config()
    with get_db_manager().get_session() as session:
        service = SpaceService(session)
        results, _ = service.list_spaces(name, None, 1, 100)
        if not results:
            results, _ = service.list_spaces(None, 1, 1, 100)

        spaces = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
            }
            for p in results
        ]

    return json.dumps(spaces, ensure_ascii=False)


@tool
def get_space_endpoints(space_id: int) -> str:
    """根据空间ID获取该空间下所有启用的API接口。返回接口列表（JSON格式），包含id、name、path、method、summary、tags、response_summary字段。response_summary展示接口返回的数据结构摘要，便于理解接口间数据依赖关系。"""
    init_database_from_config()
    with get_db_manager().get_session() as session:
        results = EndpointService(session).list_active(space_id)

        endpoints = [
            {
                "id": ep.id,
                "name": ep.name,
                "path": ep.path,
                "method": ep.method,
                "summary": ep.summary or "",
                "tags": ep.tags,
                "response_summary": _build_response_summary(ep.responses),
            }
            for ep in results
        ]

    return json.dumps(endpoints, ensure_ascii=False)


def _build_response_summary(responses_json: str) -> str:
    """从 responses JSON 中提取成功响应的 schema 摘要。

    只保留 2xx 响应的顶层属性名和类型，供 LLM 理解接口输出结构。
    """
    try:
        responses = json.loads(responses_json) if responses_json else []
    except (json.JSONDecodeError, TypeError):
        return ""

    if not responses:
        return ""

    for resp in responses:
        status_code = str(resp.get("status_code", ""))
        if not status_code.startswith("2"):
            continue

        content = resp.get("content", {})
        if not content:
            continue

        for _media_type, media_data in content.items():
            schema = media_data.get("schema", {})
            if not schema:
                continue

            properties = schema.get("properties", {})
            if properties:
                fields = []
                for name, prop in list(properties.items())[:10]:
                    prop_type = prop.get("type", "object")
                    fields.append(f"{name}({prop_type})")
                return ", ".join(fields)

            schema_type = media_data.get("type", schema.get("type", ""))
            if schema_type:
                return schema_type

    return ""
