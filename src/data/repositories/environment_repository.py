from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.environment import Environment

from src.data.repositories.base import BaseRepository


class EnvironmentRepository(BaseRepository[Environment]):
    """环境表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Environment, session)

    def get_by_name(self, name: str) -> Optional[Environment]:
        stmt = select(Environment).where(Environment.name == name)
        return self._session.scalar(stmt)

    def get_by_project_and_name(self, project_id: int, name: str) -> Optional[Environment]:
        stmt = select(Environment).where(
            Environment.project_id == project_id,
            Environment.name == name
        )
        return self._session.scalar(stmt)

    def bulk_query(
            self, project_ids: set, names: set
    ) -> List[Environment]:
        """批量查询：一次 SQL 替代 N 次循环查询"""
        stmt = select(Environment).where(
            Environment.project_id.in_(project_ids),
            Environment.name.in_(names)
        )
        return list(self._session.scalars(stmt).all())

    def get_active_environments(self) -> List[Environment]:
        stmt = select(Environment).where(Environment.status == 1)
        return list(self._session.scalars(stmt).all())

    def find_or_create(self, project_id: int, name: str, base_url: str, description: str = "") -> Environment:
        existing = self.get_by_project_and_name(project_id, name)
        if existing is not None:
            return existing
        env = Environment(project_id=project_id, name=name, base_url=base_url, description=description)
        return self.add(env)