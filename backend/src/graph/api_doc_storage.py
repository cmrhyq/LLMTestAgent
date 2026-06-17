import json
from dataclasses import dataclass
from pathlib import Path

from src import AppConfig, get_config
from src.core.database.connection import init_database_from_config
from src.core.logging import get_logger
from src.data.schemas.endpoint import EndpointCreate
from src.data.schemas.environment import EnvironmentCreate
from src.data.schemas.project import ProjectCreate
from src.data.services.endpoint_service import EndpointService
from src.data.services.environment_service import EnvironmentService
from src.data.services.project_service import ProjectService
from src.utils.parser import OpenAPIParser

logger = get_logger(__name__)


@dataclass(frozen=True)
class ParseStorageResult:
    """OpenAPI 文档解析存储的结果摘要。"""

    project_id: int
    project_name: str
    environment_count: int
    endpoint_count: int


def _get_session():
    """获取数据库会话，自动确保数据库已初始化。"""
    return init_database_from_config().get_session()


class ApiDocStorage:
    """API文档存储"""

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()

    def openapi_parse_storage(self, file_path: Path) -> ParseStorageResult:
        """
        解析 OpenAPI 文档并将结果存储到数据库。

        整个操作在单一事务中完成：project、environment、endpoint
        的写入要么全部成功，要么全部回滚。

        Args:
            file_path: OpenAPI 文档文件路径

        Returns:
            ParseStorageResult: 包含 project_id、项目名称、环境数量和端点数量。

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文档解析失败
        """
        logger.info(f"开始解析OpenAPI文档: {file_path}", path=str(file_path))
        parser = OpenAPIParser(file_path)
        logger.info(
            f"OpenAPI文档信息 - 标题: {parser.title}，base_url: {parser.base_url}",
            title=parser.title,
            base_url=parser.base_url,
        )

        project = ProjectCreate(
            name=parser.title,
            base_url=parser.base_url,
            description=parser.description,
        )

        with _get_session() as session:
            project_service = ProjectService(session)
            env_service = EnvironmentService(session)
            endpoint_service = EndpointService(session)

            project_info = project_service.create_project(project)
            if project_info.id is None:
                logger.error("创建项目失败，未获得有效的project_id", action="parse_storage")
                raise ValueError("创建项目失败，project_id 为空")

            env_list = self._build_environments(project_info.id, parser)
            if env_list:
                env_service.create_env(env_list)

            endpoint_list = self._build_endpoints(project_info.id, parser)
            if endpoint_list:
                endpoint_service.create_endpoint(endpoint_list)

        result = ParseStorageResult(
            project_id=project_info.id,
            project_name=parser.title,
            environment_count=len(env_list),
            endpoint_count=len(endpoint_list),
        )
        logger.info(
            f"OpenAPI文档解析存储完成，项目: {result.project_name}，"
            f"环境: {result.environment_count}，端点: {result.endpoint_count}",
            project=result.project_name,
            project_id=result.project_id,
            env_count=result.environment_count,
            endpoint_count=result.endpoint_count,
        )
        return result

    @staticmethod
    def _build_environments(project_id: int, parser: OpenAPIParser) -> list[EnvironmentCreate]:
        return [
            EnvironmentCreate(
                project_id=project_id,
                name=server.get("description") or f"默认环境名称_{server.get('url', '')}",
                base_url=server.get("url", ""),
                description=server.get("description", ""),
                variables=str(server.get("variables", "")),
                is_default=1 if server.get("url", "") == parser.base_url else 2,
            )
            for server in parser.servers
        ]

    @staticmethod
    def _build_endpoints(project_id: int, parser: OpenAPIParser) -> list[EndpointCreate]:
        result = []
        for ep in parser.endpoints:
            header_params = [p for p in ep.get("parameters", []) if p.get("in") == "header"]

            request_body = ep.get("request_body") or {}
            content_type = "application/json"
            if isinstance(request_body, dict) and request_body.get("content"):
                content_keys = list(request_body["content"].keys())
                if content_keys:
                    content_type = content_keys[0]

            result.append(
                EndpointCreate(
                    project_id=project_id,
                    operation_id=ep.get("operation_id", ""),
                    name=ep.get("summary", ""),
                    path=ep.get("path", ""),
                    method=ep.get("method", ""),
                    tags=json.dumps(ep.get("tags", []), ensure_ascii=False),
                    summary=ep.get("summary", ""),
                    description=ep.get("description", ""),
                    params=json.dumps(ep.get("parameters", []), ensure_ascii=False),
                    headers=json.dumps(header_params, ensure_ascii=False),
                    body=json.dumps(request_body, ensure_ascii=False),
                    responses=json.dumps(ep.get("responses", []), ensure_ascii=False),
                    security=json.dumps(ep.get("security", []), ensure_ascii=False),
                    content_type=content_type,
                    deprecated=1 if ep.get("deprecated", False) else 0,
                )
            )
        return result
