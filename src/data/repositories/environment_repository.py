from typing import Optional, List, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.environment import Environment

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class EnvironmentRepository(BaseRepository[Environment]):
    """环境表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Environment, session)

    def get_by_name(self, name: str) -> Optional[Environment]:
        stmt = select(Environment).where(Environment.name == name)
        return self._session.scalar(stmt)

    def get_active_environments(self) -> List[Environment]:
        stmt = select(Environment).where(Environment.status == 1)
        return list(self._session.scalars(stmt).all())

    def find_or_create(self, name: str, base_url: str, description: str = "") -> Environment:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        env = Environment(name=name, base_url=base_url, description=description)
        return self.add(env)