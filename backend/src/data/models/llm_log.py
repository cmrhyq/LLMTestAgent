from __future__ import annotations

from sqlalchemy import Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base, local_now
from src.utils.id import next_id


class LLMLog(Base):
    """LLM 调用记录表 - 统计每次大模型请求的 token 用量与使用模型。

    由 ``src.core.llm.llm_service.LLMService`` 在每次调用后写入
    （来源：litellm ``AIMessage.usage_metadata`` / ``response_metadata``）。
    """

    __tablename__ = "llm_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=next_id)
    model_name: Mapped[str] = mapped_column(Text, nullable=False, comment="使用的模型（如 zai/glm-4-flash）")
    provider: Mapped[str] = mapped_column(Text, default="", comment="厂商（model_name 前缀）")
    request_type: Mapped[str] = mapped_column(Text, default="", comment="调用类型：invoke/ainvoke/stream/astream/tools")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输入 token 数")
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输出 token 数")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="总 token 数")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, comment="调用耗时（毫秒）")
    success: Mapped[int] = mapped_column(Integer, default=1, comment="是否成功：1-成功 0-失败")
    error_message: Mapped[str] = mapped_column(Text, default="", comment="失败原因（成功时为空）")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)

    __table_args__ = (
        Index("idx_llm_log_model", "model_name"),
        Index("idx_llm_log_created", "created_at"),
    )
