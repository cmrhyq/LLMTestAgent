from typing import Optional, List

from pydantic import BaseModel, Field


class TestRunResponse(BaseModel):
    """TestRun 响应体"""
    id: int = Field(..., description="执行批次ID")
    project_id: Optional[int] = Field(default=None, description="所属项目ID")
    environment_id: Optional[int] = Field(default=None, description="关联环境ID")
    name: str = Field(default="", description="批次名称")
    status: str = Field(..., description="状态: pending/running/completed/failed/cancelled")
    trigger_type: str = Field(default="manual", description="触发类型: manual/scheduled/ci")
    llm_provider: str = Field(default="", description="LLM 提供商")
    llm_model: str = Field(default="", description="LLM 模型名称")
    total_cases: int = Field(default=0, description="总用例数")
    passed_cases: int = Field(default=0, description="通过数")
    failed_cases: int = Field(default=0, description="失败数")
    skipped_cases: int = Field(default=0, description="跳过数")
    error_cases: int = Field(default=0, description="错误数")
    pass_rate: float = Field(default=0.0, description="通过率 (%)")
    total_duration: float = Field(default=0.0, description="总耗时 (秒)")
    started_at: Optional[str] = Field(default=None, description="开始时间")
    finished_at: Optional[str] = Field(default=None, description="结束时间")
    error_message: str = Field(default="", description="错误信息")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class TestRunDetail(TestRunResponse):
    """TestRun 详情响应（含关联统计）"""
    project_name: Optional[str] = Field(default=None, description="项目名称")
    environment_name: Optional[str] = Field(default=None, description="环境名称")

    model_config = {"from_attributes": True}


class TestRunListResponse(BaseModel):
    """TestRun 列表响应"""
    items: List[TestRunResponse] = Field(default=[], description="执行批次列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


class TestRunQuery(BaseModel):
    """TestRun 查询参数"""
    project_id: Optional[int] = Field(default=None, description="项目ID筛选")
    status: Optional[str] = Field(default=None, description="状态筛选")
    trigger_type: Optional[str] = Field(default=None, description="触发类型筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
