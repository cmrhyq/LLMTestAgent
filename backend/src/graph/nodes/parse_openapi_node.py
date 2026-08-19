"""OpenAPI 文档解析节点。

解析 OpenAPI 文档并将项目、环境、端点信息持久化到数据库。
"""

from pathlib import Path

from src.core.config import get_config
from src.core.logging import get_logger
from src.graph.api_doc_storage import ApiDocStorage
from src.graph.constants import NodeName
from src.graph.state import AgentState

logger = get_logger(__name__)


def parse_openapi_node(state: AgentState) -> dict:
    """OpenAPI 文档解析节点。

    Args:
        state: 当前工作流状态

    Returns:
        部分状态更新（成功时包含 endpoint_count，失败时包含 error_message）
    """
    logger.info("进入OpenAPI文档解析节点", node=NodeName.PARSE_OPENAPI_DOC.value)

    try:
        api_doc_file_path = state.get("api_doc_file_path")
        if not api_doc_file_path:
            raise ValueError("api_doc_file_path 为空，无法解析 OpenAPI 文档")

        file_path = Path(api_doc_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"API 文档文件不存在: {file_path}")

        logger.info(f"开始解析并存储API文档: {file_path}", node=NodeName.PARSE_OPENAPI_DOC.value, path=str(file_path))
        config = get_config()
        storage = ApiDocStorage(config)
        result = storage.openapi_parse_storage(file_path)
        logger.info(
            "OpenAPI文档解析存储完成",
            node=NodeName.PARSE_OPENAPI_DOC.value,
            project_id=result.project_id,
            endpoint_count=result.endpoint_count,
        )
        return {
            "endpoint_count": result.endpoint_count,
            "next_node": NodeName.END.value,
        }

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"OpenAPI文档解析失败: {str(e)}", node=NodeName.PARSE_OPENAPI_DOC.value, error=str(e))
        return {"next_node": NodeName.ERROR.value, "error_message": f"OpenAPI 文档解析失败: {str(e)}"}

    except Exception as e:
        logger.error(f"OpenAPI文档解析异常: {str(e)}", node=NodeName.PARSE_OPENAPI_DOC.value, error=str(e))
        return {"next_node": NodeName.ERROR.value, "error_message": f"OpenAPI 文档解析异常: {str(e)}"}
