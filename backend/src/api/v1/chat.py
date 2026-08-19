"""安全审计 + 流式对话路由。

业务编排（审计分流、会话/消息持久化、LLM 流式生成）已下沉到
``src.data.services.chat_stream_service.ChatStreamService``，
本路由只负责校验请求体并返回 ``StreamingResponse``。
"""

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from src.core.logging import get_logger
from src.data.schemas.conversation import ChatStreamRequest
from src.data.services.chat_stream_service import ChatStreamService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/stream")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    """安全审计后流式返回大模型回答或拦截提示。

    会话与 user 消息在流式开始前落库，assistant 消息在流式结束后落库；
    会话 ID 通过响应头 X-Conversation-Id 返回。
    """
    service = ChatStreamService()
    conversation_id = await run_in_threadpool(service.ensure_conversation, body)
    return StreamingResponse(
        service.generate_stream(body.instruction, conversation_id),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Conversation-Id": str(conversation_id),
            "Access-Control-Expose-Headers": "X-Conversation-Id",
        },
    )
