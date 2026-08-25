"""工作流触发路由。

提供 OpenAPI 文档上传与解析的 HTTP 接口，业务编排见 ``WorkflowService``。
"""

from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.data.enum.workflow import TestStatus
from src.data.services.workflow_service import WorkflowService

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["工作流"])


class UploadOpenAPIResponse(BaseModel):
    """上传 OpenAPI 文档响应体。"""

    filename: str = Field(..., description="原始文件名")
    path: str = Field(..., description="服务器保存后的绝对路径")
    status: str = Field(default="uploaded", description="当前状态")
    message: str = Field(default="", description="提示信息")


class WorkflowRunStreamRequest(BaseModel):
    """流式运行工作流请求体。"""

    raw_input: str = Field(..., description="用户自然语言指令")
    include_tokens: bool = Field(
        default=False,
        description="是否输出 LLM token 级流式事件（默认仅节点级进度）",
    )


@router.post("/upload/openapi", response_model=UploadOpenAPIResponse)
async def upload_openapi(
        file: UploadFile = File(..., description="OpenAPI 文档文件（JSON/YAML）"),
):
    """上传 OpenAPI 文档并持久化保存，返回服务器路径供后续运行测试使用。"""
    service = WorkflowService()
    content = await file.read()
    path = await run_in_threadpool(service.save_upload, file.filename or "", content)

    return UploadOpenAPIResponse(
        filename=Path(file.filename or "").name,
        path=path,
        status="uploaded",
        message=f"文件 {file.filename} 上传成功",
    )


@router.post("/run/stream")
async def run_workflow_stream(body: WorkflowRunStreamRequest) -> StreamingResponse:
    """流式运行测试工作流，以 SSE（text/event-stream）格式推送进度事件。

    每个事件为 ``data: {json}\\n\\n``，事件类型见 ``TestWorkflow.astream``：
    - start：工作流启动
    - node：节点执行完成（默认输出；include_tokens=true 时改为 token 事件）
    - token：LLM 生成增量（include_tokens=true 时输出）
    - final：携带完整最终状态
    - error：执行异常
    """
    service = WorkflowService()
    return StreamingResponse(
        service.run_stream(body),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
