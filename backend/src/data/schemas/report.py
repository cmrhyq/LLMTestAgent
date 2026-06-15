from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    """Report 响应体"""

    id: int = Field(..., description="报告ID")
    run_id: int = Field(..., description="所属执行批次ID")
    format: str = Field(..., description="报告格式: excel/html/markdown/json")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(default=0, description="文件大小 (字节)")
    generated_at: str = Field(..., description="生成时间")

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """Report 列表响应"""

    items: list[ReportResponse] = Field(default=[], description="报告列表")
    total: int = Field(default=0, description="总数")
