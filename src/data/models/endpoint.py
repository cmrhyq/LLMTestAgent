from typing import Optional, List

from sqlalchemy import (
    Integer, Text, ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models import TestCase
from src.data.models.base import Base, local_now
from src.data.models.project import Project


class Endpoint(Base):
    """API 定义表"""
    __tablename__ = "endpoint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    operation_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="[]")
    summary: Mapped[Optional[str]] = mapped_column(Text, default=None)
    description: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[Optional[str]] = mapped_column(Text, default=None)
    headers: Mapped[str] = mapped_column(Text, default="{}")
    body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="P1")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=local_now)

    project: Mapped[Project] = relationship(back_populates="endpoint")
    test_cases: Mapped[List[TestCase]] = relationship(back_populates="endpoint")

    __table_args__ = (
        CheckConstraint("method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')", name="ck_api_method"),
        CheckConstraint("priority IN ('P0','P1','P2')", name="ck_api_priority"),
        Index("idx_endpoint_project", "project_id"),
        Index("idx_endpoint_operation_id", "operation_id"),
    )