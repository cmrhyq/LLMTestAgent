"""chat 流式编排服务。

承接 ``api/v1/chat.py`` 的业务逻辑：安全审计分流、会话与消息持久化、LLM 流式生成。
路由层只负责校验请求体与返回 ``StreamingResponse``。
"""

from collections.abc import AsyncIterator, Callable
from typing import cast

from fastapi.concurrency import run_in_threadpool

from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.schemas.conversation import ConversationCreate
from src.data.services.conversation_service import ConversationService
from src.graph.constants import NodeName
from src.graph.nodes.security_audit_node import security_audit_node
from src.graph.state import AgentState
from src.prompts.loader import get_loader
from src.utils.json_utils import parse_llm_json_object

logger = get_logger(__name__)

# 拦截提示文案
SECURITY_RISK_MESSAGE = "⚠️ 检测到您的输入存在安全风险，无法处理该请求。请调整后重试。"
NON_TESTING_MESSAGE = "抱歉，我只处理 API 测试相关的内容，无法回答 API 测试以外的问题。"
AUDIT_ERROR_MESSAGE = "抱歉，处理您的请求时发生错误，请稍后重试。"

# API 测试助手系统提示（模板：chat_assistant_system.yaml）
_ASSISTANT_SYSTEM_PROMPT = get_loader().load_simple_prompt_sync("chat_assistant_system.yaml")


class ChatStreamService:
    """chat 流式编排：安全审计分流 + 会话/消息持久化 + LLM 流式生成。

    Args:
        audit_func: 安全审计可调用对象（默认 ``security_audit_node``），测试可注入。
        llm_client_factory: 返回 LLM 客户端的工厂（默认 ``src.get_llm_client``），测试可注入。
    """

    def __init__(self, audit_func: Callable[[AgentState], dict] | None = None, llm_client_factory=None) -> None:
        self._audit: Callable[[AgentState], dict] = audit_func or security_audit_node
        self._llm_client_factory = llm_client_factory or _default_llm_client

    # ------------------------------------------------------------------
    # 纯判断函数
    # ------------------------------------------------------------------

    @staticmethod
    def is_blocked_by_security(audit: dict) -> bool:
        """根据审计结果判断是否命中安全风险。

        同时兼容 security_analysis.is_safe 布尔字段与 overall_verdict.action，
        任一命中风险即视为拦截。
        """
        security = audit.get("security_analysis") or {}
        verdict = audit.get("overall_verdict") or {}
        if security.get("is_safe") is False:
            return True
        return verdict.get("action") == "block"

    @staticmethod
    def is_non_testing(audit: dict) -> bool:
        """根据审计结果判断是否为非 API 测试内容。"""
        api_testing = audit.get("api_testing_analysis") or {}
        return api_testing.get("is_api_testing") is False

    # ------------------------------------------------------------------
    # 会话与消息持久化
    # ------------------------------------------------------------------

    def ensure_conversation(self, body) -> int:
        """确保存在会话并返回 conversation_id；同时把 user 消息落库。

        若 body.conversation_id 为空则新建会话。整个操作在独立 DB 事务中完成。
        """
        try:
            with get_db_manager().get_session() as session:
                service = ConversationService(session)
                conversation_id = body.conversation_id
                if conversation_id is None:
                    conversation = service.create_conversation(
                        ConversationCreate(project_id=body.project_id, title="", mode=body.mode)
                    )
                    conversation_id = conversation.id
                service.append_message(conversation_id, role="user", content=body.instruction)
                return conversation_id
        except RuntimeError as exc:
            # 对未初始化数据库的轻量调用（例如只验证审计分支的测试）允许继续，
            # 生产应用会在启动阶段初始化数据库，正常不会走到这里。
            logger.warning("会话持久化暂不可用，继续执行流式对话", error=str(exc))
            return body.conversation_id or 0

    def load_history(self, conversation_id: int) -> list[dict[str, str]]:
        """加载会话的历史消息，转为 LLM messages 格式（仅 user/assistant）。"""
        try:
            with get_db_manager().get_session() as session:
                messages = ConversationService(session).list_messages(conversation_id)
                return [{"role": m.role, "content": m.content} for m in messages if m.role in ("user", "assistant")]
        except RuntimeError as exc:
            logger.warning("会话历史暂不可用，使用空历史", error=str(exc))
            return []

    def save_assistant_message(self, conversation_id: int, content: str) -> None:
        """把 assistant 回复落库。"""
        try:
            with get_db_manager().get_session() as session:
                ConversationService(session).append_message(conversation_id, role="assistant", content=content)
        except RuntimeError as exc:
            logger.warning("assistant 消息持久化暂不可用", error=str(exc))

    # ------------------------------------------------------------------
    # 流式生成
    # ------------------------------------------------------------------

    async def generate_stream(self, instruction: str, conversation_id: int) -> AsyncIterator[str]:
        """根据审计结果生成流式文本，并在结束时持久化 assistant 消息。

        先在线程池执行阻塞的安全审计节点，再按判定分支流式产出内容。
        """
        collected: list[str] = []
        try:
            # 审计节点内部为阻塞的 llm 调用，放入线程池避免阻塞事件循环
            state = cast(AgentState, {"raw_input": instruction})
            audit_state = await run_in_threadpool(self._audit, state)

            if audit_state.get("next_node") == NodeName.ERROR.value:
                logger.warning("安全审计节点返回异常，拦截请求", error=audit_state.get("error_message", ""))
                collected.append(AUDIT_ERROR_MESSAGE)
                yield AUDIT_ERROR_MESSAGE
                return

            audit = parse_llm_json_object(audit_state.get("audit_result", ""))
            if not audit:
                logger.warning("安全审计结果解析为空，出于安全考虑拦截请求")
                collected.append(AUDIT_ERROR_MESSAGE)
                yield AUDIT_ERROR_MESSAGE
                return

            if self.is_blocked_by_security(audit):
                logger.info(
                    "Prompt 命中安全风险，拦截",
                    summary=(audit.get("security_analysis") or {}).get("summary", ""),
                )
                collected.append(SECURITY_RISK_MESSAGE)
                yield SECURITY_RISK_MESSAGE
                return

            if self.is_non_testing(audit):
                logger.info("Prompt 非 API 测试内容，拒绝处理")
                collected.append(NON_TESTING_MESSAGE)
                yield NON_TESTING_MESSAGE
                return

            logger.info("Prompt 通过安全审计且为测试内容，进入大模型流式回答")
            history = await run_in_threadpool(self.load_history, conversation_id)
            messages = [{"role": "system", "content": _ASSISTANT_SYSTEM_PROMPT}, *history]
            async for token in self._llm_client_factory().achat_stream(messages):
                collected.append(token)
                yield token
        except Exception as e:
            logger.error("流式对话处理失败", error=str(e))
            collected.append(AUDIT_ERROR_MESSAGE)
            yield AUDIT_ERROR_MESSAGE
        finally:
            answer = "".join(collected)
            if answer:
                try:
                    await run_in_threadpool(self.save_assistant_message, conversation_id, answer)
                except Exception as e:  # noqa: BLE001
                    logger.error("assistant 消息持久化失败", error=str(e), conversation_id=conversation_id)


def _default_llm_client():
    """默认 LLM 客户端工厂（延迟导入避免循环依赖）。"""
    from src import get_llm_client

    return get_llm_client()
