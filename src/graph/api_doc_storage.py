from pathlib import Path
from typing import Optional

from src import AppConfig, get_config
from src.core.database.connection import get_session_from_config
from src.core.logging import get_logger
from src.data.schemas.endpoint import EndpointCreate
from src.data.schemas.environment import EnvironmentCreate
from src.data.schemas.project import ProjectCreate
from src.data.services.endpoint_service import EndpointService
from src.data.services.environment_service import EnvironmentService
from src.data.services.project_service import ProjectService
from src.utils.parser import OpenAPIParser

logger = get_logger(__name__)


class ApiDocStorage(object):
    """
    API文档存储

    Attributes:
        config: 应用配置
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化用例生成器

        Args:
            config: 应用配置
        """
        self.config = config or get_config()
        self._session = get_session_from_config()
        self.project_service = ProjectService(self._session)
        self.env_service = EnvironmentService(self._session)
        self.endpoint_service = EndpointService(self._session)

    def openapi_parse_storage(self, file_path: Path):
        try:
            logger.info("开始解析OpenAPI文档")
            parser = OpenAPIParser(file_path)
            logger.info(f"OpenAPI Document Title: {parser.title}")
            logger.info(f"OpenAPI Document Description: {parser.description}")
            logger.info(f"OpenAPI Document Base Url: {parser.base_url}")
            project = ProjectCreate(
                name=parser.title,
                base_url=parser.base_url,
                description=parser.description,
            )
            logger.info("开始存储OpenAPI文档解析结果")
            project_info = self.project_service.create_project(project)
            if project_info.id is not None:
                env_list, endpoint_list = [], []
                for server in parser.servers:
                    url = server.get("url", "")
                    description = server.get("description", "")
                    variables = server.get("variables", "")
                    is_default = 1 if url == parser.base_url else 2

                    env_list.append(EnvironmentCreate(
                        project_id=project_info.id,
                        name=description,
                        base_url=url,
                        description=description,
                        variables=variables,
                        is_default=is_default
                    ))
                self.env_service.create_env(env_list)

                for endpoint in parser.endpoints:
                    endpoint_list.append(EndpointCreate(
                        project_id=project_info.id,
                        operation_id=endpoint.get("operation_id", ""),
                        name=endpoint.get("summary", ""),
                        path=endpoint.get("path", ""),
                        method=endpoint.get("method", ""),
                        tags=str(endpoint.get("tags", "[]")),
                        summary=endpoint.get("summary", ""),
                        description=endpoint.get("description", ""),
                        params=str(endpoint.get("parameters", "{}")),
                        headers=endpoint.get("headers", "{}"),
                        body=endpoint.get("request_body", "{}"),
                    ))
                self.endpoint_service.create_endpoint(endpoint_list)
                logger.info(f"存储OpenAPI文档解析结果成功")
        except Exception as e:
            logger.error(f"解析存储OpenAPI文档错误：{e}")


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent.parent
    input_file = project_root / "input" / "test_yaml.yaml"
    api_storage = ApiDocStorage()
    api_storage.openapi_parse_storage(input_file)