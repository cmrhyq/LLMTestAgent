from sqlalchemy.orm import Session

from src.data.models.base import local_now
from src.data.models.conversation import Conversation
from src.data.models.message import Message
from src.data.repositories import ConversationRepository, MessageRepository
from src.data.schemas.conversation import ConversationCreate

_TITLE_MAX_LEN = 30


class ConversationService:
    """会话业务逻辑：创建会话、追加消息并维护会话元数据。"""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)

    def create_conversation(self, data: ConversationCreate) -> Conversation:
        """创建新会话。"""
        conversation = Conversation(
            project_id=data.project_id,
            title=data.title or "",
            mode=data.mode or "Ask",
        )
        return self.conv_repo.add(conversation)

    def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        meta: str = "{}",
    ) -> Message:
        """向会话追加一条消息，并更新会话的 last_message_at/updated_at；

        若会话标题为空且为首条 user 消息，则用内容截断生成标题。
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta=meta,
        )
        self.msg_repo.add(message)

        now = local_now()
        conversation = self.conv_repo.get_by_id(conversation_id)
        if conversation is not None:
            conversation.last_message_at = now
            conversation.updated_at = now
            if role == "user" and not conversation.title:
                conversation.title = self._make_title(content)
            self.conv_repo.update_entity(conversation)

        return message

    @staticmethod
    def _make_title(content: str) -> str:
        """从消息内容生成会话标题（去除换行并截断）。"""
        normalized = " ".join(content.split()).strip()
        if len(normalized) > _TITLE_MAX_LEN:
            return normalized[:_TITLE_MAX_LEN] + "…"
        return normalized or "新对话"
