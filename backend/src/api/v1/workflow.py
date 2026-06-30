"""工作流触发路由。

提供 OpenAPI 文档解析和测试执行的 HTTP 接口。
"""

import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.core.config import get_config
from src.core.logging import get_logger
from src.data.models.test_run import TestRun
from src.data.repositories import TestRunRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["工作流"])

_running_tasks: dict[int, dict[str, Any]] = {}
_tasks_lock = threading.Lock()

# 上传的 OpenAPI 文档持久化目录，供 Run Test 在运行时读取
_UPLOAD_DIR = Path("uploads")
_ALLOWED_SUFFIXES = (".json", ".yaml", ".yml")


class RunTestRequest(BaseModel):
    """触发测试执行请求体。"""

    instruction: str = Field(..., min_length=1, description="自然语言测试指令")
    api_doc_path: str | None = Field(default=None, description="已解析的 OpenAPI 文档路径")


class RunTestResponse(BaseModel):
    """触发测试执行响应体。"""

    run_id: int = Field(..., description="测试运行ID")
    status: str = Field(default="pending", description="当前状态")
    message: str = Field(default="", description="提示信息")


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


class WorkflowStatusResponse(BaseModel):
    """工作流状态查询响应。"""

    run_id: int
    status: str = "unknown"
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    error_message: str = ""
    started_at: str | None = None
    finished_at: str | None = None


def _execute_workflow_task(run_id: int, instruction: str, api_doc_path: str | None):
    """后台执行工作流任务。"""
    from src.core.database.connection import get_db_manager
    from src.workflow import TestWorkflow

    manager = get_db_manager()
    with manager.get_session() as session:
        run_repo = TestRunRepository(session)
        run_repo.update_status(run_id, "running")

    try:
        config = get_config()
        workflow = TestWorkflow(config)
        doc_path = Path(api_doc_path) if api_doc_path else None

        result = workflow.run(raw_input=instruction, api_doc_file_path=doc_path)

        error_message = result.get("error_message", "")
        with manager.get_session() as session:
            run_repo = TestRunRepository(session)
            if error_message:
                run_repo.update_status(run_id, "failed", error_message=error_message)
            else:
                summary = result.get("test_summary", {})
                run_repo.update_statistics(
                    run_db_id=run_id,
                    total=summary.get("total", 0),
                    passed=summary.get("passed", 0),
                    failed=summary.get("failed", 0),
                    skipped=summary.get("skipped", 0),
                    error=summary.get("error", 0),
                    pass_rate=summary.get("pass_rate", 0.0),
                    total_duration=summary.get("total_duration", 0.0),
                )
                run_repo.update_status(run_id, "completed")

    except Exception as e:
        logger.error(f"工作流后台执行失败: {e}", run_id=run_id, error=str(e))
        with manager.get_session() as session:
            run_repo = TestRunRepository(session)
            run_repo.update_status(run_id, "failed", error_message=str(e))
    finally:
        with _tasks_lock:
            _running_tasks.pop(run_id, None)


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


@router.post("/run/test", response_model=RunTestResponse)
def run_test(
    body: RunTestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """触发测试执行（异步后台运行）。"""
    run_repo = TestRunRepository(db)
    test_run = TestRun(
        name=f"API测试: {body.instruction[:50]}",
        status="pending",
        trigger_type="manual",
    )
    created_run = run_repo.add(test_run)
    db.commit()
    run_id = created_run.id

    with _tasks_lock:
        _running_tasks[run_id] = {"status": "pending"}

    background_tasks.add_task(_execute_workflow_task, run_id, body.instruction, body.api_doc_path)

    return RunTestResponse(
        run_id=run_id,
        status="pending",
        message="测试任务已提交，后台执行中",
    )


@router.get("/status/{run_id}", response_model=WorkflowStatusResponse)
def get_workflow_status(run_id: int, db: Session = Depends(get_db)):
    """查询工作流执行状态。"""
    repo = TestRunRepository(db)
    run = repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="测试运行不存在")

    return WorkflowStatusResponse(
        run_id=run.id,
        status=run.status,
        total_cases=run.total_cases,
        passed_cases=run.passed_cases,
        failed_cases=run.failed_cases,
        pass_rate=run.pass_rate,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
