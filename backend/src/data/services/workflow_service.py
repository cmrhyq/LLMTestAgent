"""工作流触发服务。

承接 ``api/v1/workflow.py`` 的业务：OpenAPI 文档上传保存与解析编排。
路由层只负责收文件、调 Service、返回 schema。
"""

import tempfile
import uuid
from pathlib import Path

from src.core.config import get_config
from src.core.errors import ValidationError
from src.core.logging import get_logger
from src.workflow import TestWorkflow

logger = get_logger(__name__)

# 上传的 OpenAPI 文档持久化目录，供后续解析时读取
_UPLOAD_DIR = Path("uploads")
_ALLOWED_SUFFIXES = (".json", ".yaml", ".yml")


class WorkflowService:
    """OpenAPI 文档上传与解析编排。"""

    def save_upload(self, filename: str, content: bytes) -> str:
        """校验并保存上传的 OpenAPI 文档，返回绝对路径。

        Args:
            filename: 原始文件名
            content: 文件内容

        Returns:
            服务器保存后的绝对路径

        Raises:
            ValidationError: 文件名或后缀非法
        """
        if not filename:
            raise ValidationError("文件名不能为空")

        # 仅保留文件名部分，防止路径遍历（如 ../../etc/passwd）
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise ValidationError("仅支持 JSON/YAML 格式文件")

        _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        saved_path = _UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
        saved_path.write_bytes(content)

        resolved = saved_path.resolve()
        logger.info("OpenAPI 文档上传成功", filename=safe_name, path=str(resolved))
        return str(resolved)

    def parse_openapi(self, filename: str, content: bytes) -> dict:
        """上传并解析 OpenAPI 文档，返回解析结果。

        Args:
            filename: 原始文件名
            content: 文件内容

        Returns:
            {"endpoint_count": int}

        Raises:
            ValidationError: 文件名非法或解析失败
        """
        if not filename:
            raise ValidationError("文件名不能为空")

        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise ValidationError("仅支持 JSON/YAML 格式文件")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="openapi_") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            config = get_config()
            workflow = TestWorkflow(config)
            result = workflow.run(
                raw_input="解析这份API文档",
                api_doc_file_path=tmp_path,
            )

            error_message = result.get("error_message", "")
            if error_message:
                raise ValidationError(f"解析失败: {error_message}")

            logger.info("OpenAPI 文档解析成功", filename=filename, endpoint_count=result.get("endpoint_count", 0))
            return {"endpoint_count": result.get("endpoint_count", 0)}
        finally:
            tmp_path.unlink(missing_ok=True)
