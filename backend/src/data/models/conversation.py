from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import Base, local_now
from src.utils.id import next_id

if TYPE_CHECKING:
    from src.data.models.message import Message
    from src.data.models.space import Space


class Conversation(Base):
    """会话表 - 记录一次多轮对话的元数据"""

    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=next_id)
    space_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("space.id", ondelete="CASCADE"), default=None)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="Ask")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_message_at: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)

    space: Mapped[Space | None] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at, Message.id",
    )

    __table_args__ = (
        CheckConstraint("mode IN ('Ask','Plan','Run')", name="ck_conversation_mode"),
        CheckConstraint("status IN (0,1)", name="ck_conversation_status"),
        Index("idx_conversation_space", "space_id"),
    )
