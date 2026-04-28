from typing import Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.test_summary import TestSummary

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class TestSummaryRepository(BaseRepository[TestSummary]):
    """测试摘要表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestSummary, session)

    def get_by_run(self, run_id: int) -> Optional[TestSummary]:
        stmt = select(TestSummary).where(TestSummary.run_id == run_id)
        return self._session.scalar(stmt)