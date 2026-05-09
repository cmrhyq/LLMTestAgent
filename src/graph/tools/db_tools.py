"""数据库查询 LangChain Tools。

提供 search_project 和 get_project_endpoints 两个工具，
供 LLM 通过 function calling 自动调用。
"""

import json
from typing import List

from langchain_core.tools import tool
from sqlalchemy import select

from src import get_config
from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.models.endpoint import Endpoint
from src.data.models.project import Project

logger = get_logger(__name__)


def _ensure_db_initialized() -> None:
    """确保数据库已初始化，未初始化时从配置自动完成。"""
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


@tool
def search_project(name: str) -> str:
    """根据名称搜索项目，支持模糊匹配。返回匹配的项目列表（JSON格式），包含id、name、base_url、description字段。"""
    _ensure_db_initialized()
    with get_db_manager().get_session() as session:
        stmt = select(Project).where(Project.name.contains(name))
        results: List[Project] = list(session.scalars(stmt).all())

        if not results:
            stmt_all = select(Project).where(Project.status == 1)
            results = list(session.scalars(stmt_all).all())

        projects = [
            {
                "id": p.id,
                "name": p.name,
                "base_url": p.base_url,
                "description": p.description,
            }
            for p in results
        ]

    return json.dumps(projects, ensure_ascii=False)


@tool
def get_project_endpoints(project_id: int) -> str:
    """根据项目ID获取该项目下所有启用的API接口。返回接口列表（JSON格式），包含id、name、path、method、summary、tags字段。"""
    _ensure_db_initialized()
    with get_db_manager().get_session() as session:
        stmt = select(Endpoint).where(
            Endpoint.project_id == project_id,
            Endpoint.status == 1,
        )
        results: List[Endpoint] = list(session.scalars(stmt).all())

        endpoints = [
            {
                "id": ep.id,
                "name": ep.name,
                "path": ep.path,
                "method": ep.method,
                "summary": ep.summary or "",
                "tags": ep.tags,
            }
            for ep in results
        ]

    return json.dumps(endpoints, ensure_ascii=False)
