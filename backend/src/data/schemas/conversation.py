from pydantic import BaseModel, Field

from src.data.schemas.common import PaginatedResponse
from src.data.schemas.message import MessageResponse


class ConversationBase(BaseModel):
    """Conversation 基础字段"""

    space_id: int | None = Field(default=None, description="所属空间ID（可空）")
    title: str = Field(default="", description="会话标题")
    mode: str = Field(default="Ask", description="模式: Ask / Plan")


class ConversationCreate(ConversationBase):
    """创建 Conversation 请求体"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "space_id": None,
                    "title": "",
                    "mode": "Ask",
                }
            ]
        }
    }


class ConversationUpdate(BaseModel):
    """更新 Conversation 请求体（所有字段可选）"""

    title: str | None = Field(default=None, description="会话标题")
    mode: str | None = Field(default=None, description="模式: Ask / Plan")
    status: int | None = Field(default=None, description="状态: 1-正常, 0-删除")


class ConversationResponse(ConversationBase):
    """Conversation 响应体"""

    id: int = Field(..., description="会话ID")
    status: int = Field(..., description="状态: 1-正常, 0-删除")
    last_message_at: str | None = Field(default=None, description="最后一条消息时间")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    """Conversation 详情响应（含消息列表）"""

    messages: list[MessageResponse] = Field(default=[], description="消息列表")

    model_config = {"from_attributes": True}


class ConversationListResponse(PaginatedResponse[ConversationResponse]):
    """Conversation 列表响应"""


class ChatStreamRequest(BaseModel):
    """流式对话请求体。"""

    instruction: str = Field(..., min_length=1, description="用户输入的 prompt")
    api_doc_path: str | None = Field(default=None, description="可选的已上传 OpenAPI 文档路径")
    conversation_id: int | None = Field(default=None, description="会话 ID；缺省时自动新建会话")
    mode: str = Field(default="Ask", description="模式: Ask / Plan")
    space_id: int | None = Field(default=None, description="新建会话时所属空间 ID（可选）")
