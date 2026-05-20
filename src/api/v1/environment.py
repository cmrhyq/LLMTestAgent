"""环境管理路由。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.models.environment import Environment
from src.data.repositories import EnvironmentRepository
from src.data.schemas.environment import (
    EnvironmentCreate,
    EnvironmentUpdate,
    EnvironmentResponse,
    EnvironmentListResponse,
)

router = APIRouter(prefix="/environments", tags=["环境管理"])


@router.post("/", response_model=EnvironmentResponse, status_code=201)
def create_environment(body: EnvironmentCreate, db: Session = Depends(get_db)):
    """创建环境配置。"""
    repo = EnvironmentRepository(db)
    existing = repo.get_by_project_and_name(body.project_id, body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"环境已存在: {body.name}")
    env = Environment(**body.model_dump())
    created = repo.add(env)
    return created


@router.get("/", response_model=EnvironmentListResponse)
def list_environments(
    project_id: Optional[int] = Query(default=None, description="项目ID筛选"),
    keyword: Optional[str] = Query(default=None, description="关键字搜索"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询环境列表（分页）。"""
    repo = EnvironmentRepository(db)
    all_envs = repo.get_all(limit=1000, offset=0)

    filtered = all_envs
    if project_id is not None:
        filtered = [e for e in filtered if e.project_id == project_id]
    if keyword:
        kw = keyword.lower()
        filtered = [
            e for e in filtered
            if kw in (e.name or "").lower()
            or kw in (e.description or "").lower()
        ]

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start: start + page_size]
    return EnvironmentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{env_id}", response_model=EnvironmentResponse)
def get_environment(env_id: int, db: Session = Depends(get_db)):
    """获取环境详情。"""
    repo = EnvironmentRepository(db)
    env = repo.get_by_id(env_id)
    if env is None:
        raise HTTPException(status_code=404, detail="环境不存在")
    return env


@router.put("/{env_id}", response_model=EnvironmentResponse)
def update_environment(env_id: int, body: EnvironmentUpdate, db: Session = Depends(get_db)):
    """更新环境配置。"""
    repo = EnvironmentRepository(db)
    env = repo.get_by_id(env_id)
    if env is None:
        raise HTTPException(status_code=404, detail="环境不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(env, field, value)
    updated = repo.update_entity(env)
    return updated


@router.delete("/{env_id}", status_code=204)
def delete_environment(env_id: int, db: Session = Depends(get_db)):
    """删除环境。"""
    repo = EnvironmentRepository(db)
    success = repo.delete_by_id(env_id)
    if not success:
        raise HTTPException(status_code=404, detail="环境不存在")
