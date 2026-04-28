from datetime import datetime
from sqlalchemy import Integer, DateTime, Boolean, func, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src import TestCase
from src.data.models.endpoint import Endpoint
from src.data.models.environment import Environment
from src.data.models.project import Project
from src.data.models.test_run import TestRun


def local_now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


def _update_timestamp(mapper, connection, target):
    """ORM 事件：更新 updated_at 时间戳"""
    if hasattr(target, "updated_at"):
        target.updated_at = local_now()


for _model in (Project, Environment, Endpoint, TestRun, TestCase):
    event.listen(_model, "before_update", _update_timestamp)


class Base(DeclarativeBase):
    """所有模型的声明性基类"""
    pass


class TimestampMixin:
    """时间戳混入"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """软删除混入"""
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BaseModel(Base, TimestampMixin):
    """带公共字段的抽象基类"""
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}