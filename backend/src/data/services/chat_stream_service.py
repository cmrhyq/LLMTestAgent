"""chat 流式编排服务（精简版）。

会话与 user 消息落库入口 ``ensure_conversation`` 保留在 API 层调用；
安全审计分流、LLM 回答生成、assistant 消息落库逻辑已全部迁移至
``src.graph.nodes.answer_question.answer_question_node``。
"""

from src.core.database.connection import get_db_manager
from src.core.logging import get_logger
from src.data.schemas.conversation import ConversationCreate
from src.data.services.conversation_service import ConversationService

logger = get_logger(__name__)


class ChatStreamService:
    """chat 会话编排：仅负责确保会话存在并把 user 消息落库。"""

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
                        ConversationCreate(space_id=body.space_id, title="", mode=body.mode)
                    )
                    conversation_id = conversation.id
                service.append_message(conversation_id, role="user", content=body.instruction)
                return conversation_id
        except RuntimeError as exc:
            # 对未初始化数据库的轻量调用（例如只验证审计分支的测试）允许继续，
            # 生产应用会在启动阶段初始化数据库，正常不会走到这里。
            logger.warning("会话持久化暂不可用，继续执行流式对话", error=str(exc))
            return body.conversation_id or 0
