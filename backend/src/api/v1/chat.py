"""安全审计 + 流式对话路由。

接收用户 prompt，先经 security_audit_node 做安全与意图审计：
- 命中安全风险 → 流式返回安全风险提示
- 非 API 测试内容 → 流式返回「不处理 API 测试以外内容」提示
- 安全且为测试内容 → 交给大模型流式返回回答
"""

from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src import get_llm_client
from src.core.logging import get_logger
from src.graph.nodes.security_audit_node import security_audit_node
from src.graph.state import AgentState
from src.utils.llm_utils import parse_llm_json_object

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])

# 拦截提示文案
_SECURITY_RISK_MESSAGE = "⚠️ 检测到您的输入存在安全风险，无法处理该请求。请调整后重试。"
_NON_TESTING_MESSAGE = "抱歉，我只处理 API 测试相关的内容，无法回答 API 测试以外的问题。"
_AUDIT_ERROR_MESSAGE = "抱歉，处理您的请求时发生错误，请稍后重试。"

# API 测试助手系统提示
_ASSISTANT_SYSTEM_PROMPT = (
    "你是一名专业的 API 测试助手，擅长接口测试用例设计、测试策略、"
    "自动化测试脚本编写以及 HTTP 请求/响应构造与断言。"
    "请针对用户的 API 测试相关问题给出专业、准确、可落地的解答。"
    "请使用 Markdown 格式组织回答；代码示例使用 fenced code block 并标注语言（如 json、bash、python）。"
    "表格请使用 GFM 表格语法（| 列 |），不要用代码块包裹表格或整段回答；"
    "ASCII 框线图可放在 text 代码块中，但代码块外应继续使用正常 Markdown（标题、加粗、列表等）。"
)


class ChatStreamRequest(BaseModel):
    """流式对话请求体。"""

    instruction: str = Field(..., min_length=1, description="用户输入的 prompt")
    api_doc_path: str | None = Field(default=None, description="可选的已上传 OpenAPI 文档路径")


def _is_blocked_by_security(audit: dict) -> bool:
    """根据审计结果判断是否命中安全风险。

    同时兼容 security_analysis.is_safe 布尔字段与 overall_verdict.action，
    任一命中风险即视为拦截。
    """
    security = audit.get("security_analysis") or {}
    verdict = audit.get("overall_verdict") or {}
    if security.get("is_safe") is False:
        return True
    return verdict.get("action") == "block"


def _is_non_testing(audit: dict) -> bool:
    """根据审计结果判断是否为非 API 测试内容。"""
    api_testing = audit.get("api_testing_analysis") or {}
    return api_testing.get("is_api_testing") is False


async def _generate_stream(instruction: str) -> AsyncIterator[str]:
    """根据审计结果生成流式文本。

    先在线程池执行阻塞的安全审计节点，再按判定分支流式产出内容。
    """
    try:
        # security_audit_node 内部为阻塞的 llm_client.chat()，放入线程池避免阻塞事件循环
        # 该节点仅读取 state["raw_input"]，此处构造最小状态并 cast 为 AgentState
        state = cast(AgentState, {"raw_input": instruction})
        audit_state = await run_in_threadpool(security_audit_node, state)

        if audit_state.get("current_step") == "error":
            logger.warning("安全审计节点返回异常，拦截请求", error=audit_state.get("error_message", ""))
            yield _AUDIT_ERROR_MESSAGE
            return

        audit = parse_llm_json_object(audit_state.get("audit_result", ""))
        if not audit:
            logger.warning("安全审计结果解析为空，出于安全考虑拦截请求")
            yield _AUDIT_ERROR_MESSAGE
            return

        if _is_blocked_by_security(audit):
            logger.info("Prompt 命中安全风险，拦截", summary=(audit.get("security_analysis") or {}).get("summary", ""))
            yield _SECURITY_RISK_MESSAGE
            return

        if _is_non_testing(audit):
            logger.info("Prompt 非 API 测试内容，拒绝处理")
            yield _NON_TESTING_MESSAGE
            return

        logger.info("Prompt 通过安全审计且为测试内容，进入大模型流式回答")
        messages = [
            {"role": "system", "content": _ASSISTANT_SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
        async for token in get_llm_client().achat_stream(messages):
            yield token
    except Exception as e:
        logger.error("流式对话处理失败", error=str(e))
        yield _AUDIT_ERROR_MESSAGE


@router.post("/stream")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    """安全审计后流式返回大模型回答或拦截提示。"""
    return StreamingResponse(
        _generate_stream(body.instruction),
        media_type="text/plain; charset=utf-8",
    )
