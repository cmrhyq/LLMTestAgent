from typing import Optional, List, TypeVar

from sqlalchemy import select, and_, literal
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.endpoint import Endpoint

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class EndpointRepository(BaseRepository[Endpoint]):
    """API 定义表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Endpoint, session)

    def check_duplicate(self, project_id: int, path: str, method: str) -> bool:
        """
        数据查重
        """
        stmt = (
            select(literal(1))
            .select_from(Endpoint)
            .where(
                and_(
                    Endpoint.project_id == project_id,
                    Endpoint.path == path,
                    Endpoint.method == method.upper(),
                )
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None

    def bulk_query(
            self, project_ids: set, paths: set, methods: set
    ) -> List[Endpoint]:
        """批量查询：一次 SQL 替代 N 次循环查询"""
        stmt = select(Endpoint).where(
            Endpoint.project_id.in_(project_ids),
            Endpoint.path.in_(paths),
            Endpoint.method.in_(methods),
        )
        return list(self._session.scalars(stmt).all())

    def get_by_project(self, project_id: int, active_only: bool = True) -> List[Endpoint]:
        conditions = [Endpoint.project_id == project_id]
        if active_only:
            conditions.append(Endpoint.status == 1)
        stmt = select(Endpoint).where(and_(*conditions))
        return list(self._session.scalars(stmt).all())

    def get_by_operation_id(self, project_id: int, operation_id: str, version: int = 1) -> Optional[Endpoint]:
        stmt = select(Endpoint).where(
            and_(
                Endpoint.project_id == project_id,
                Endpoint.operation_id == operation_id,
                Endpoint.version == version,
            )
        )
        return self._session.scalar(stmt)

    def get_by_method(self, project_id: int, method: str) -> List[Endpoint]:
        stmt = select(Endpoint).where(
            and_(Endpoint.project_id == project_id, Endpoint.method == method)
        )
        return list(self._session.scalars(stmt).all())