"""安全审计 + 流式对话路由（按 mode 分流）。

- ``mode=run``：走完整 graph（意图判断 → run 则测试执行 / ask 则回答），
  SSE 事件流输出（``data: {json}\\n\\n``），结束后把测试摘要落库为 assistant 消息
- ``mode=ask``：走 ``answer_question_node``（安全审计 + 回答），text/plain 分块输出
- ``mode=plan``：占位（功能待定）

会话与 user 消息在流式开始前落库（``ChatStreamService.ensure_conversation``），
会话 ID 通过响应头 X-Conversation-Id 返回。
"""

import json
from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from src.core.config import get_config
from src.core.database.database_manager import get_db_manager
from src.core.logging import get_logger
from src.data.schemas.conversation import ChatStreamRequest
from src.data.services.chat_stream_service import ChatStreamService
from src.data.services.conversation_service import ConversationService
from src.graph.nodes.answer_question import AUDIT_ERROR_MESSAGE, answer_question_node
from src.graph.state import AgentState
from src.workflow import TestWorkflow

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])

# 模拟打字机的分块大小（节点内为同步完整生成，API 层分块输出保持流式体验）
_CHUNK_SIZE = 8
PLAN_PENDING_MESSAGE = "计划模式开发中，请使用 Run 或 Ask 模式。"


async def _generate_answer_stream(instruction: str, conversation_id: int) -> AsyncIterator[str]:
    """ask 模式：调用 answer_question_node 生成完整回答，并按块输出。

    节点为同步实现（内部 LLM 调用为阻塞式），放入线程池避免阻塞事件循环。
    """
    try:
        state = cast(AgentState, {"raw_input": instruction, "conversation_id": conversation_id or None})
        result = await run_in_threadpool(answer_question_node, state)
        answer = result.get("answer_content") or AUDIT_ERROR_MESSAGE
        for i in range(0, len(answer), _CHUNK_SIZE):
            yield answer[i : i + _CHUNK_SIZE]
    except Exception as e:
        logger.error("流式回答生成失败", error=str(e))
        yield AUDIT_ERROR_MESSAGE


def _build_run_summary(final_state: dict[str, Any]) -> str:
    """从 graph 最终状态构造测试摘要（用于 assistant 消息落库）。"""
    if final_state.get("user_intent") != "run":
        # run 模式下 LLM 判定为 ask：直接回存回答内容
        return final_state.get("answer_content") or "（未产生回答）"

    summary = final_state.get("test_results_summary") or {}
    lines = [
        f"测试执行完成：共 {summary.get('total', 0)} 条用例，"
        f"通过 {summary.get('passed', 0)}，失败 {summary.get('failed', 0)}，"
        f"通过率 {summary.get('pass_rate', 0.0):.1%}",
    ]
    if final_state.get("report_path"):
        lines.append(f"报告：{final_state['report_path']}")
    return "\n".join(lines)


async def _generate_run_stream(
    instruction: str,
    conversation_id: int,
    space_id: int | None,
) -> AsyncIterator[str]:
    """run 模式：走完整 graph，SSE 事件流输出，结束后落库 assistant 摘要。

    事件与 ``/workflows/run/stream`` 一致：``data: {json}\\n\\n``，
    type 为 start / node / final / error。
    """
    workflow = TestWorkflow(get_config())
    final_state: dict[str, Any] | None = None
    try:
        async for event in workflow.astream(instruction, space_id=space_id):
            if event.get("type") == "final":
                final_state = event.get("state")
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
    except Exception as e:
        logger.error("run 模式流式执行失败", error=str(e))
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        return

    # 流式结束后把结果摘要落库为 assistant 消息（所有问答均存库）
    if final_state and conversation_id:
        summary = _build_run_summary(final_state)
        try:
            with get_db_manager().get_session() as session:
                ConversationService(session).append_message(conversation_id, role="assistant", content=summary)
        except RuntimeError as exc:
            logger.warning("assistant 消息持久化暂不可用", error=str(exc))


async def _generate_plain_stream(message: str) -> AsyncIterator[str]:
    """直接输出固定文本（占位模式）。"""
    for i in range(0, len(message), _CHUNK_SIZE):
        yield message[i : i + _CHUNK_SIZE]


@router.post("/stream")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    """按 mode 分流返回流式响应。

    - run：SSE 结构化事件（graph 测试流程/意图回答）
    - ask：text/plain 大模型回答
    - plan：text/plain 占位提示
    """
    service = ChatStreamService()
    conversation_id = await run_in_threadpool(service.ensure_conversation, body)
    mode = (body.mode or "Run").lower()

    if mode == "run":
        generator = _generate_run_stream(body.instruction, conversation_id, body.space_id)
        media_type = "text/event-stream; charset=utf-8"
    elif mode == "plan":
        generator = _generate_plain_stream(PLAN_PENDING_MESSAGE)
        media_type = "text/plain; charset=utf-8"
    else:  # ask
        generator = _generate_answer_stream(body.instruction, conversation_id)
        media_type = "text/plain; charset=utf-8"

    return StreamingResponse(
        generator,
        media_type=media_type,
        headers={
            "X-Conversation-Id": str(conversation_id),
            "Access-Control-Expose-Headers": "X-Conversation-Id",
        },
    )
