"""接口管理路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.models.endpoint import Endpoint
from src.data.repositories import EndpointRepository
from src.data.schemas.endpoint import (
    EndpointCreate,
    EndpointListResponse,
    EndpointResponse,
    EndpointUpdate,
)

router = APIRouter(prefix="/endpoints", tags=["接口管理"])


@router.post("/", response_model=EndpointResponse, status_code=201)
def create_endpoint(body: EndpointCreate, db: Session = Depends(get_db)):
    """创建单个接口定义。"""
    repo = EndpointRepository(db)
    if repo.check_duplicate(body.project_id, body.path, body.method):
        raise HTTPException(
            status_code=409,
            detail=f"接口已存在: {body.method} {body.path}",
        )
    endpoint = Endpoint(**body.model_dump())
    created = repo.add(endpoint)
    return created


@router.post("/batch", response_model=list[EndpointResponse], status_code=201)
def batch_create_endpoints(body: list[EndpointCreate], db: Session = Depends(get_db)):
    """批量创建接口定义。"""
    from src.data.services.endpoint_service import EndpointService

    service = EndpointService(db)
    results = service.create_endpoint(body)
    return results


@router.get("/", response_model=EndpointListResponse)
def list_endpoints(
    project_id: int | None = Query(default=None, description="项目ID筛选"),
    method: str | None = Query(default=None, description="HTTP 方法筛选"),
    keyword: str | None = Query(default=None, description="关键字搜索"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询接口列表（分页）。"""
    repo = EndpointRepository(db)

    if project_id is not None:
        all_endpoints = repo.get_by_project(project_id, active_only=False)
    else:
        all_endpoints = repo.get_all(limit=5000, offset=0)

    filtered = all_endpoints
    if method:
        filtered = [e for e in filtered if e.method.upper() == method.upper()]
    if keyword:
        kw = keyword.lower()
        filtered = [
            e
            for e in filtered
            if kw in (e.name or "").lower() or kw in (e.path or "").lower() or kw in (e.summary or "").lower()
        ]

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start : start + page_size]
    return EndpointListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{endpoint_id}", response_model=EndpointResponse)
def get_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    """获取接口详情。"""
    repo = EndpointRepository(db)
    endpoint = repo.get_by_id(endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="接口不存在")
    return endpoint


@router.put("/{endpoint_id}", response_model=EndpointResponse)
def update_endpoint(endpoint_id: int, body: EndpointUpdate, db: Session = Depends(get_db)):
    """更新接口。"""
    repo = EndpointRepository(db)
    endpoint = repo.get_by_id(endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="接口不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if isinstance(value, (list, dict)):
                import json

                setattr(endpoint, field, json.dumps(value, ensure_ascii=False))
            else:
                setattr(endpoint, field, value)
    updated = repo.update_entity(endpoint)
    return updated


@router.delete("/{endpoint_id}", status_code=204)
def delete_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    """删除接口。"""
    repo = EndpointRepository(db)
    success = repo.delete_by_id(endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="接口不存在")
