"""项目管理路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from src.data.services import ProjectService

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    """创建项目。"""
    return ProjectService(db).create_project(body)


@router.get("/", response_model=ProjectListResponse)
def list_projects(
    keyword: str | None = Query(default=None, description="关键字搜索"),
    status: int | None = Query(default=None, description="状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询项目列表（分页）。"""
    items, total = ProjectService(db).list_projects(keyword, status, page, page_size)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items], total=total, page=page, page_size=page_size
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情。"""
    return ProjectService(db).get_or_raise(project_id, "项目不存在")


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目。"""
    return ProjectService(db).update_project(project_id, body.model_dump(exclude_unset=True))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目及其关联的环境、端点、测试运行等数据。"""
    ProjectService(db).delete_project(project_id)
