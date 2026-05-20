"""测试运行查询路由。"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.repositories import TestRunRepository, TestCaseRepository, TestResultRepository

router = APIRouter(prefix="/test-runs", tags=["测试运行"])


class TestRunResponse(BaseModel):
    """测试运行响应体。"""
    id: int
    project_id: Optional[int] = None
    environment_id: Optional[int] = None
    name: str = ""
    status: str = "pending"
    trigger_type: str = "manual"
    llm_provider: str = ""
    llm_model: str = ""
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    pass_rate: float = 0.0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_duration: float = 0.0
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""

    model_config = {"from_attributes": True}


class TestRunListResponse(BaseModel):
    """测试运行列表响应。"""
    items: List[TestRunResponse] = Field(default=[])
    total: int = 0
    page: int = 1
    page_size: int = 20


class TestCaseBrief(BaseModel):
    """测试用例摘要。"""
    id: int
    name: str = ""
    method: str = ""
    path: str = ""
    priority: str = ""
    status: str = ""
    created_at: str = ""

    model_config = {"from_attributes": True}


class TestResultBrief(BaseModel):
    """测试结果摘要。"""
    id: int
    test_case_id: Optional[int] = None
    status: str = ""
    status_code: Optional[int] = None
    duration: float = 0.0
    assertion_passed: int = 0
    assertion_failed: int = 0
    error_message: str = ""
    created_at: str = ""

    model_config = {"from_attributes": True}


class TestRunDetail(TestRunResponse):
    """测试运行详情（含用例和结果）。"""
    test_cases: List[TestCaseBrief] = Field(default=[])
    test_results: List[TestResultBrief] = Field(default=[])


@router.get("/", response_model=TestRunListResponse)
def list_test_runs(
    project_id: Optional[int] = Query(default=None, description="项目ID筛选"),
    status: Optional[str] = Query(default=None, description="状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询测试运行列表（分页）。"""
    repo = TestRunRepository(db)

    if project_id is not None:
        all_runs = repo.get_by_project(project_id, limit=1000)
    elif status is not None:
        all_runs = repo.get_by_status(status)
    else:
        all_runs = repo.get_all(limit=1000, offset=0)

    total = len(all_runs)
    start = (page - 1) * page_size
    items = all_runs[start: start + page_size]
    return TestRunListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{run_id}", response_model=TestRunDetail)
def get_test_run(run_id: int, db: Session = Depends(get_db)):
    """获取测试运行详情（含用例和结果）。"""
    repo = TestRunRepository(db)
    run = repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="测试运行不存在")

    cases = run.test_cases if run.test_cases else []
    results = run.test_results if run.test_results else []

    return TestRunDetail(
        **{k: v for k, v in TestRunResponse.model_validate(run).model_dump().items()},
        test_cases=[TestCaseBrief.model_validate(c) for c in cases],
        test_results=[TestResultBrief.model_validate(r) for r in results],
    )
