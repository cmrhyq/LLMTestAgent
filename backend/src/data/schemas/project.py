from pydantic import BaseModel, Field, field_validator

from src.data.schemas.common import (
    BatchDeleteRequest,
    BatchUpdateStatusRequest,
    PaginatedResponse,
    strip_trailing_slash,
)

# ==================== 基础 Schema ====================


class ProjectBase(BaseModel):
    """Project 基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="项目名称（唯一）")
    base_url: str = Field(..., description="基础URL地址")
    description: str | None = Field(default="", description="项目描述")
    status: int = Field(default=1, description="状态: 1-启用, 0-禁用")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v):
        return strip_trailing_slash(v)


# ==================== 创建 Schema ====================


class ProjectCreate(ProjectBase):
    """创建 Project 请求体"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "用户服务",
                    "base_url": "https://api.example.com/v1",
                    "description": "用户中心微服务",
                    "status": 1,
                }
            ]
        }
    }


# ==================== 更新 Schema ====================


class ProjectUpdate(BaseModel):
    """更新 Project 请求体（所有字段可选）"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="项目名称")
    base_url: str | None = Field(default=None, description="基础URL地址")
    description: str | None = Field(default=None, description="项目描述")
    status: int | None = Field(default=None, description="状态: 1-启用, 0-禁用")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v):
        return strip_trailing_slash(v)


# ==================== 响应 Schema ====================


class ProjectResponse(ProjectBase):
    """Project 响应体"""

    id: int = Field(..., description="项目ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    """Project 详情响应（含统计信息）"""

    endpoint_count: int | None = Field(default=0, description="API 数量")
    test_run_count: int | None = Field(default=0, description="测试执行次数")

    model_config = {"from_attributes": True}


# ==================== 列表/分页 Schema ====================


class ProjectListResponse(PaginatedResponse[ProjectResponse]):
    """Project 列表响应"""


class ProjectQuery(BaseModel):
    """Project 查询参数"""

    name: str | None = Field(default=None, description="项目名称模糊搜索")
    status: int | None = Field(default=None, description="状态筛选")
    keyword: str | None = Field(default=None, description="关键字搜索(名称/描述)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ==================== 批量操作 Schema ====================


class ProjectBatchDelete(BatchDeleteRequest):
    """批量删除请求"""


class ProjectBatchUpdateStatus(BatchUpdateStatusRequest):
    """批量更新状态请求"""
