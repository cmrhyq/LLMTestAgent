from typing import Optional, List, TypeVar

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.test_case import TestCase

from src.data.repositories.base import BaseRepository

T = TypeVar("T", bound=Base)


class TestCaseRepository(BaseRepository[TestCase]):
    """测试用例表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestCase, session)

    def get_by_run(self, run_id: int) -> List[TestCase]:
        stmt = select(TestCase).where(TestCase.run_id == run_id)
        return list(self._session.scalars(stmt).all())

    def get_by_case_id(self, case_id: str) -> Optional[TestCase]:
        stmt = select(TestCase).where(TestCase.case_id == case_id)
        return self._session.scalar(stmt)

    def get_by_scenario(self, run_id: int, scenario_type: str) -> List[TestCase]:
        stmt = select(TestCase).where(
            and_(TestCase.run_id == run_id, TestCase.scenario_type == scenario_type)
        )
        return list(self._session.scalars(stmt).all())

    def count_by_run(self, run_id: int) -> int:
        stmt = select(func.count()).select_from(TestCase).where(TestCase.run_id == run_id)
        return self._session.scalar(stmt) or 0