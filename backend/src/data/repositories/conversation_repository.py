from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.data.models.conversation import Conversation
from src.data.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """会话表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Conversation, session)

    def list_by_project(self, project_id: int | None, status: int | None = 1) -> list[Conversation]:
        """按项目查询会话列表，按 last_message_at / created_at 倒序。"""
        stmt = select(Conversation)
        if project_id is not None:
            stmt = stmt.where(Conversation.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(
            Conversation.last_message_at.desc().nullslast(),
            Conversation.created_at.desc(),
        )
        return list(self._session.scalars(stmt).all())

    def get_with_messages(self, conversation_id: int) -> Conversation | None:
        """获取会话及其全部消息（按消息创建时间升序加载）。"""
        stmt = (
            select(Conversation).where(Conversation.id == conversation_id).options(selectinload(Conversation.messages))
        )
        return self._session.scalar(stmt)
