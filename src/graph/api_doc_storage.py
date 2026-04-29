from pathlib import Path
from typing import Optional

from src import AppConfig, get_config
from src.core.database import init_database
from src.core.logging import get_logger
from src.data.schemas.project import ProjectCreate
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
        self.db = init_database(
            db_url=self.config.database.url,
            echo=self.config.database.echo,
            pool_size=self.config.database.pool_size,
            max_overflow=self.config.database.max_overflow,
            pool_timeout=self.config.database.pool_timeout,
            pool_recycle=self.config.database.pool_recycle,
        )
        self.service = ProjectService(self.db.create_session())

    def openapi_parse_storage(self, file_path: Path):
        try:
            parser = OpenAPIParser(file_path)
            logger.info(f"title: {parser.title}")
            logger.info(f"description: {parser.description}")
            logger.info(f"base url: {parser.base_url}")
            project = ProjectCreate(
                name=parser.title,
                base_url=parser.base_url,
                description=parser.description,
            )
            info = self.service.create_project(project)
            if info.id is not None:
                for server in parser.servers:
                    url = server.get("url", "")
                    description = server.get("description", "")
                    variables = server.get("variables", {})
                    
        except Exception as e:
            logger.error(f"解析存储OpenAPI文档错误：{e}")


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent.parent
    input_file = project_root / "input" / "test_yaml.yaml"
    api_storage = ApiDocStorage()
    api_storage.openapi_parse_storage(input_file)