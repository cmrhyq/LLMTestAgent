from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ==================== 基础 Schema ====================

class ProjectBase(BaseModel):
    """Project 基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称（唯一）")
    base_url: str = Field(..., description="基础URL地址")
    description: Optional[str] = Field(default="", description="项目描述")
    status: int = Field(default=1, description="状态: 1-启用, 0-禁用")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """去除末尾斜杠，保持统一格式"""
        if isinstance(v, str):
            return v.rstrip("/")
        return v


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
                    "status": 1
                }
            ]
        }
    }


# ==================== 更新 Schema ====================

class ProjectUpdate(BaseModel):
    """更新 Project 请求体（所有字段可选）"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="项目名称")
    base_url: Optional[str] = Field(default=None, description="基础URL地址")
    description: Optional[str] = Field(default=None, description="项目描述")
    status: Optional[int] = Field(default=None, description="状态: 1-启用, 0-禁用")

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v):
        if isinstance(v, str):
            return v.rstrip("/")
        return v


# ==================== 响应 Schema ====================

class ProjectResponse(ProjectBase):
    """Project 响应体"""
    id: int = Field(..., description="项目ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {
        "from_attributes": True
    }


class ProjectDetail(ProjectResponse):
    """Project 详情响应（含统计信息）"""
    endpoint_count: Optional[int] = Field(default=0, description="API 数量")
    test_run_count: Optional[int] = Field(default=0, description="测试执行次数")

    model_config = {
        "from_attributes": True
    }


# ==================== 列表/分页 Schema ====================

class ProjectListResponse(BaseModel):
    """Project 列表响应"""
    items: List[ProjectResponse] = Field(default=[], description="项目列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


class ProjectQuery(BaseModel):
    """Project 查询参数"""
    name: Optional[str] = Field(default=None, description="项目名称模糊搜索")
    status: Optional[int] = Field(default=None, description="状态筛选")
    keyword: Optional[str] = Field(default=None, description="关键字搜索(名称/描述)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ==================== 批量操作 Schema ====================

class ProjectBatchDelete(BaseModel):
    """批量删除请求"""
    ids: List[int] = Field(..., min_length=1, description="项目ID列表")


class ProjectBatchUpdateStatus(BaseModel):
    """批量更新状态请求"""
    ids: List[int] = Field(..., min_length=1, description="项目ID列表")
    status: int = Field(..., description="目标状态: 1-启用, 0-禁用")