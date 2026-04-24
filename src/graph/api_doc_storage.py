from pathlib import Path
from typing import Optional

from src import AppConfig, get_config
from src.core.logging import get_logger
from src.data.enum.models import Priority
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
        self.openapi = OpenAPIParser(default_priority=Priority.P1)

    def openapi_parse_storage(self, file_path: Path):
        try:
            parse_result = self.openapi.parse(file_path)
            result = parse_result[2]

            for warn in result.warnings:
                logger.warning(warn)

            if result.is_valid:
                base_url = parse_result[0]
                api_info = parse_result[1]
                for api in api_info:
                    logger.info(api)
            else:
                for error in result.errors:
                    logger.error(error)
        except Exception as e:
            logger.error(f"解析存储OpenAPI文档错误：{e}")


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent.parent
    input_file = project_root / "input" / "test_yaml.yaml"
    api_storage = ApiDocStorage()
    api_storage.openapi_parse_storage(input_file)