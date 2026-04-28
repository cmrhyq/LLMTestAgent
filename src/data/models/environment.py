from typing import List

from sqlalchemy import (
    Integer, Text, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models import TestRun
from src.data.models.base import Base, local_now


class Environment(Base):
    """测试环境表"""
    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    variables: Mapped[str] = mapped_column(Text, default="{}")
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)

    test_runs: Mapped[List[TestRun]] = relationship(back_populates="environment")

    __table_args__ = (
        Index("idx_env_project", "project_id"),
    )