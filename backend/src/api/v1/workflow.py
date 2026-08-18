"""工作流触发路由。

提供 OpenAPI 文档上传与解析的 HTTP 接口。
"""

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.core.config import get_config
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["工作流"])

# 上传的 OpenAPI 文档持久化目录，供后续解析时读取
_UPLOAD_DIR = Path("uploads")
_ALLOWED_SUFFIXES = (".json", ".yaml", ".yml")


class ParseOpenAPIRequest(BaseModel):
    """解析 OpenAPI 文档响应体。"""

    run_id: int | None = None
    status: str = "completed"
    message: str = ""
    endpoints_count: int = 0


class UploadOpenAPIResponse(BaseModel):
    """上传 OpenAPI 文档响应体。"""

    filename: str = Field(..., description="原始文件名")
    path: str = Field(..., description="服务器保存后的绝对路径")
    status: str = Field(default="uploaded", description="当前状态")
    message: str = Field(default="", description="提示信息")


@router.post("/upload/openapi", response_model=UploadOpenAPIResponse)
async def upload_openapi(
    file: UploadFile = File(..., description="OpenAPI 文档文件（JSON/YAML）"),
):
    """上传 OpenAPI 文档并持久化保存，返回服务器路径供后续运行测试使用。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 仅保留文件名部分，防止路径遍历（如 ../../etc/passwd）
    safe_name = Path(file.filename).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 JSON/YAML 格式文件")

    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = _UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"

    content = await file.read()
    saved_path.write_bytes(content)

    resolved = saved_path.resolve()
    logger.info("OpenAPI 文档上传成功", filename=safe_name, path=str(resolved))

    return UploadOpenAPIResponse(
        filename=safe_name,
        path=str(resolved),
        status="uploaded",
        message=f"文件 {safe_name} 上传成功",
    )


@router.post("/parse/openapi", response_model=ParseOpenAPIRequest)
async def parse_openapi(
    file: UploadFile = File(..., description="OpenAPI 文档文件（JSON/YAML）"),
    db: Session = Depends(get_db),
):
    """上传并解析 OpenAPI 文档，将接口定义存入数据库。"""
    from src.workflow import TestWorkflow

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".json", ".yaml", ".yml"):
        raise HTTPException(status_code=400, detail="仅支持 JSON/YAML 格式文件")

    content = await file.read()
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
            raise HTTPException(status_code=500, detail=f"解析失败: {error_message}")

        return ParseOpenAPIRequest(
            status="completed",
            message=f"文档 {file.filename} 解析成功",
            endpoints_count=result.get("selected_endpoints", 0),
        )
    finally:
        tmp_path.unlink(missing_ok=True)
