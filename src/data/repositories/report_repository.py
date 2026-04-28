from typing import Optional, List, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.report import Report

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class ReportRepository(BaseRepository[Report]):
    """报告记录表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Report, session)

    def get_by_run(self, run_id: int) -> List[Report]:
        stmt = select(Report).where(Report.run_id == run_id)
        return list(self._session.scalars(stmt).all())
