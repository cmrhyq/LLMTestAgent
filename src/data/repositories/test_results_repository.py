from typing import List, TypeVar

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.test_result import TestResult

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class TestResultRepository(BaseRepository[TestResult]):
    """测试结果表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestResult, session)

    def get_by_run(self, run_id: int) -> List[TestResult]:
        stmt = select(TestResult).where(TestResult.run_id == run_id)
        return list(self._session.scalars(stmt).all())

    def get_by_test_case(self, test_case_id: int) -> List[TestResult]:
        stmt = select(TestResult).where(TestResult.test_case_id == test_case_id)
        return list(self._session.scalars(stmt).all())

    def get_by_status(self, run_id: int, status: str) -> List[TestResult]:
        stmt = select(TestResult).where(
            and_(TestResult.run_id == run_id, TestResult.status == status)
        )
        return list(self._session.scalars(stmt).all())

    def get_failed_results(self, run_id: int) -> List[TestResult]:
        stmt = select(TestResult).where(
            and_(TestResult.run_id == run_id, TestResult.status.in_(["failed", "error"]))
        )
        return list(self._session.scalars(stmt).all())