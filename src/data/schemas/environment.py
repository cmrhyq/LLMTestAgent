import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ==================== 基础 Schema ====================


class EnvironmentBase(BaseModel):
    """Environment 基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="环境名称")
    base_url: str = Field(..., description="环境基础URL")
    description: str | None = Field(default="", description="环境描述")
    variables: str = Field(default="", description="环境变量键值对")
    is_default: int = Field(default=1, description="是否默认环境: 1-是, 2-否")
    status: int = Field(default=1, description="状态: 1=启用，2=禁用，3=已删除")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if isinstance(v, str):
            return v.rstrip("/")
        return v


# ==================== 创建 Schema ====================


class EnvironmentCreate(EnvironmentBase):
    """创建 Environment 请求体"""

    project_id: int = Field(..., description="所属项目ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "project_id": 1,
                    "name": "开发环境",
                    "base_url": "https://dev-api.example.com",
                    "description": "开发联调环境",
                    "variables": {"token": "dev_token_xxx", "timeout": 30, "debug": True},
                    "is_default": 0,
                    "status": 1,
                }
            ]
        }
    }


# ==================== 更新 Schema ====================


class EnvironmentUpdate(BaseModel):
    """更新 Environment 请求体（所有字段可选）"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="环境名称")
    base_url: str | None = Field(default=None, description="环境基础URL")
    description: str | None = Field(default=None, description="环境描述")
    variables: dict[str, Any] | None = Field(default=None, description="环境变量键值对")
    is_default: int | None = Field(default=None, description="是否默认环境: 1-是, 0-否")
    status: int | None = Field(default=None, description="状态: 1-启用, 2-禁用")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v):
        if isinstance(v, str):
            return v.rstrip("/")
        return v

    @field_validator("variables", mode="before")
    @classmethod
    def parse_variables(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


# ==================== 响应 Schema ====================


class EnvironmentResponse(EnvironmentBase):
    """Environment 响应体"""

    id: int = Field(..., description="环境ID")
    project_id: int = Field(..., description="所属项目ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class EnvironmentDetail(EnvironmentResponse):
    """Environment 详情响应（含统计信息）"""

    test_run_count: int | None = Field(default=0, description="关联测试执行次数")

    model_config = {"from_attributes": True}


# ==================== 列表/分页 Schema ====================


class EnvironmentListResponse(BaseModel):
    """Environment 列表响应"""

    items: list[EnvironmentResponse] = Field(default=[], description="环境列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


class EnvironmentQuery(BaseModel):
    """Environment 查询参数"""

    project_id: int | None = Field(default=None, description="项目ID筛选")
    name: str | None = Field(default=None, description="环境名称模糊搜索")
    is_default: int | None = Field(default=None, description="是否默认环境筛选")
    status: int | None = Field(default=None, description="状态筛选")
    keyword: str | None = Field(default=None, description="关键字搜索(名称/描述)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ==================== 批量操作 Schema ====================


class EnvironmentBatchDelete(BaseModel):
    """批量删除请求"""

    ids: list[int] = Field(..., min_length=1, description="环境ID列表")


class EnvironmentBatchUpdateStatus(BaseModel):
    """批量更新状态请求"""

    ids: list[int] = Field(..., min_length=1, description="环境ID列表")
    status: int = Field(..., description="目标状态: 1-启用, 0-禁用")
