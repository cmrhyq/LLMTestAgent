"""测试报告路由。"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.repositories import ReportRepository, TestResultRepository, TestRunRepository

router = APIRouter(prefix="/reports", tags=["测试报告"])


class TestRunBrief(BaseModel):
    """测试运行摘要（嵌入报告详情）。"""

    id: int
    name: str = ""
    status: str = "pending"
    llm_provider: str = ""
    llm_model: str = ""
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    pass_rate: float = 0.0
    total_duration: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None

    model_config = {"from_attributes": True}


class TestResultDetail(BaseModel):
    """测试结果完整信息。"""

    id: int
    case_id: str = ""
    case_name: str = ""
    status: str = ""
    request_url: str = ""
    request_method: str = ""
    request_headers: str = "{}"
    request_body: str | None = None
    query_params: str | None = None
    response_status_code: int | None = None
    response_headers: str = "{}"
    response_body: str | None = None
    response_time: float = 0.0
    error_message: str = ""
    retry_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    """报告列表项。"""

    id: int
    run_id: int
    format: str = ""
    file_size: int = 0
    generated_at: str = ""
    test_run_name: str = ""

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """报告列表响应。"""

    items: list[ReportResponse] = Field(default=[])
    total: int = 0
    page: int = 1
    page_size: int = 20


class ReportDetailResponse(BaseModel):
    """报告详情响应（含测试运行和结果数据）。"""

    id: int
    run_id: int
    format: str = ""
    file_size: int = 0
    generated_at: str = ""
    test_run: TestRunBrief
    test_results: list[TestResultDetail] = Field(default=[])

    model_config = {"from_attributes": True}


@router.get("/", response_model=ReportListResponse)
def list_reports(
    run_id: int | None = Query(default=None, description="按测试运行ID筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询报告列表（分页）。"""
    report_repo = ReportRepository(db)
    test_run_repo = TestRunRepository(db)

    if run_id is not None:
        all_reports = report_repo.get_by_run(run_id)
    else:
        all_reports = report_repo.get_all(limit=1000, offset=0)

    total = len(all_reports)
    start = (page - 1) * page_size
    page_items = all_reports[start : start + page_size]

    items = []
    for report in page_items:
        test_run = test_run_repo.get_by_id(report.run_id)
        run_name = test_run.name if test_run else ""
        items.append(
            ReportResponse(
                id=report.id,
                run_id=report.run_id,
                format=report.format,
                file_size=report.file_size,
                generated_at=report.generated_at,
                test_run_name=run_name,
            )
        )

    return ReportListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    """获取报告详情（含测试运行统计和完整测试结果）。"""
    report_repo = ReportRepository(db)
    report = report_repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    test_run_repo = TestRunRepository(db)
    test_run = test_run_repo.get_by_id(report.run_id)
    if test_run is None:
        raise HTTPException(status_code=404, detail="关联的测试运行不存在")

    test_result_repo = TestResultRepository(db)
    results = test_result_repo.get_by_run(report.run_id)

    return ReportDetailResponse(
        id=report.id,
        run_id=report.run_id,
        format=report.format,
        file_size=report.file_size,
        generated_at=report.generated_at,
        test_run=TestRunBrief.model_validate(test_run),
        test_results=[TestResultDetail.model_validate(r) for r in results],
    )


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """下载报告文件。"""
    report_repo = ReportRepository(db)
    report = report_repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    filename = f"test_report_{report.run_id}.{report.format}"
    media_type = "text/html" if report.format == "html" else "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
