"""OpenAPI 文档解析节点。

解析 OpenAPI 文档并将项目、环境、端点信息持久化到数据库。
"""

from pathlib import Path

from src.core.config import get_config
from src.core.logging import get_logger
from src.graph.api_doc_storage import ApiDocStorage
from src.graph.state import AgentState

logger = get_logger(__name__)


def parse_openapi_node(state: AgentState) -> dict:
    """OpenAPI 文档解析节点。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新（成功时为空字典，失败时包含 error_message）
    """
    logger.info("进入 OpenAPI 文档解析节点")

    try:
        api_doc_file_path = state.get("api_doc_file_path")
        if not api_doc_file_path:
            raise ValueError("api_doc_file_path 为空，无法解析 OpenAPI 文档")

        file_path = Path(api_doc_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"API 文档文件不存在: {file_path}")

        logger.info(f"开始解析并存储 API 文档: {file_path}")
        config = get_config()
        storage = ApiDocStorage(config)
        storage.openapi_parse_storage(file_path)
        logger.info("OpenAPI 文档解析并存储完成")
        return {
            "current_step": "end",
        }

    except (FileNotFoundError, ValueError) as e:
        error_msg = f"OpenAPI 文档解析失败: {str(e)}"
        logger.error(error_msg)
        return {
            "current_step": "error",
            "error_message": error_msg
        }

    except Exception as e:
        error_msg = f"OpenAPI 文档解析异常: {str(e)}"
        logger.error(error_msg)
        return {
            "current_step": "error",
            "error_message": error_msg
        }
