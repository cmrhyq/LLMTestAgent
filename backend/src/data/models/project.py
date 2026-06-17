from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import Base, local_now
from src.utils.id import next_id

if TYPE_CHECKING:
    from src.data.models.endpoint import Endpoint
    from src.data.models.environment import Environment
    from src.data.models.test_run import TestRun


class Project(Base):
    """项目表 - 管理多个被测服务"""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=next_id)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)

    endpoints: Mapped[list[Endpoint]] = relationship(back_populates="project", cascade="all, delete-orphan")
    environments: Mapped[list[Environment]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_runs: Mapped[list[TestRun]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_project_name", "name"),)
