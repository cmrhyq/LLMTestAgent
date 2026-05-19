from src.data.enum.workflow import HttpMethod, Priority
from src.utils.id.snow_id_utils import SnowflakeIdGenerator
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import json

snow_id = SnowflakeIdGenerator(datacenter_id=1, worker_id=1)


# ==================== 基础 Schema ====================

class EndpointBase(BaseModel):
    """Endpoint 基础字段"""
    operation_id: str = Field(..., description="操作ID，唯一标识")
    name: str = Field(..., description="API 名称")
    path: str = Field(..., description="API 路径")
    method: str = Field(..., description="HTTP 方法")
    tags: str = Field(default="[]", description="标签列表")
    summary: Optional[str] = Field(default="", description="摘要")
    description: Optional[str] = Field(default="", description="描述")
    params: Optional[str] = Field(default="{}", description="查询参数定义")
    headers: Optional[str] = Field(default="{}", description="请求头定义")
    body: Optional[str] = Field(default="{}", description="请求体定义")
    responses: str = Field(default="[]", description="响应定义 JSON 数组")
    security: str = Field(default="[]", description="接口级认证方案 JSON 数组")
    content_type: str = Field(default="application/json", description="请求体 Content-Type")
    deprecated: int = Field(default=0, description="是否已废弃: 0=正常, 1=已废弃")
    status: int = Field(default=1, description="状态: 1=启用，2=禁用，3=已删除, 4=已废弃")


# ==================== 创建 Schema ====================

class EndpointCreate(EndpointBase):
    """创建 Endpoint 请求体"""
    project_id: int = Field(default=None, description="所属项目ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": 1,
                    "operation_id": "getUserById",
                    "name": "获取用户详情",
                    "path": "/api/v1/users/{id}",
                    "method": "GET",
                    "tags": ["用户管理"],
                    "summary": "根据ID获取用户信息",
                    "description": "通过用户ID查询用户详细信息",
                    "params": {
                        "id": {
                            "type": "integer",
                            "required": True,
                            "description": "用户ID"
                        }
                    },
                    "headers": {
                        "Authorization": "Bearer {{token}}"
                    },
                    "body": None,
                    "priority": "P1",
                    "status": 1
                }
            ]
        }
    }


# ==================== 更新 Schema ====================

class EndpointUpdate(BaseModel):
    """更新 Endpoint 请求体（所有字段可选）"""
    operation_id: Optional[str] = Field(default=None, description="操作ID")
    name: Optional[str] = Field(default=None, description="API 名称")
    path: Optional[str] = Field(default=None, description="API 路径")
    method: Optional[HttpMethod] = Field(default=None, description="HTTP 方法")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    summary: Optional[str] = Field(default=None, description="摘要")
    description: Optional[str] = Field(default=None, description="描述")
    params: Optional[dict] = Field(default=None, description="查询参数定义")
    headers: Optional[dict] = Field(default=None, description="请求头定义")
    body: Optional[dict] = Field(default=None, description="请求体定义")
    responses: Optional[list] = Field(default=None, description="响应定义")
    security: Optional[list] = Field(default=None, description="接口级认证方案")
    content_type: Optional[str] = Field(default=None, description="请求体 Content-Type")
    deprecated: Optional[int] = Field(default=None, description="是否已废弃")
    status: Optional[int] = Field(default=None, description="状态")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_validator("params", "headers", "body", mode="before")
    @classmethod
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_validator("responses", "security", mode="before")
    @classmethod
    def parse_list_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


# ==================== 响应 Schema ====================

class EndpointResponse(EndpointBase):
    """Endpoint 响应体"""
    id: int = Field(..., description="Endpoint ID")
    project_id: int = Field(..., description="所属项目ID")
    version: int = Field(default=1, description="版本号")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {
        "from_attributes": True
    }


class EndpointDetail(EndpointResponse):
    """Endpoint 详情响应（含关联的测试用例数量）"""
    test_case_count: Optional[int] = Field(default=0, description="关联测试用例数量")

    model_config = {
        "from_attributes": True
    }


# ==================== 列表/分页 Schema ====================

class EndpointListResponse(BaseModel):
    """Endpoint 列表响应"""
    items: List[EndpointResponse] = Field(default=[], description="Endpoint 列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


class EndpointQuery(BaseModel):
    """Endpoint 查询参数"""
    project_id: Optional[int] = Field(default=None, description="项目ID")
    method: Optional[HttpMethod] = Field(default=None, description="HTTP 方法筛选")
    status: Optional[int] = Field(default=None, description="状态筛选")
    tags: Optional[str] = Field(default=None, description="标签筛选")
    keyword: Optional[str] = Field(default=None, description="关键字搜索(名称/路径/描述)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ==================== 批量操作 Schema ====================

class EndpointBatchDelete(BaseModel):
    """批量删除请求"""
    ids: List[int] = Field(..., min_length=1, description="Endpoint ID 列表")


class EndpointBatchUpdateStatus(BaseModel):
    """批量更新状态请求"""
    ids: List[int] = Field(..., min_length=1, description="Endpoint ID 列表")
    status: int = Field(..., description="目标状态: 1-启用, 0-禁用")
