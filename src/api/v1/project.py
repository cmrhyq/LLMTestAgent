"""项目管理路由。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.models.project import Project
from src.data.repositories import ProjectRepository
from src.data.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

router = APIRouter(prefix="/projects", tags=["项目管理"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    """创建项目。"""
    repo = ProjectRepository(db)
    existing = repo.get_by_name(body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"项目名称已存在: {body.name}")
    project = Project(**body.model_dump())
    created = repo.add(project)
    return created


@router.get("/", response_model=ProjectListResponse)
def list_projects(
    keyword: Optional[str] = Query(default=None, description="关键字搜索"),
    status: Optional[int] = Query(default=None, description="状态筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询项目列表（分页）。"""
    repo = ProjectRepository(db)
    all_projects = repo.get_all(limit=1000, offset=0)

    filtered = all_projects
    if status is not None:
        filtered = [p for p in filtered if p.status == status]
    if keyword:
        filtered = [
            p for p in filtered
            if keyword.lower() in (p.name or "").lower()
            or keyword.lower() in (p.description or "").lower()
        ]

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start: start + page_size]
    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情。"""
    repo = ProjectRepository(db)
    project = repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目。"""
    repo = ProjectRepository(db)
    project = repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    updated = repo.update_entity(project)
    return updated


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """删除项目。"""
    repo = ProjectRepository(db)
    success = repo.delete_by_id(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
