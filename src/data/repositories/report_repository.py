from typing import Optional, List, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.base import Base
from src.data.models.report import Report

from src.data.repositories.base import BaseRepository

T = TypeVar("T", bound=Base)


class ReportRepository(BaseRepository[Report]):
    """报告记录表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Report, session)

    def get_by_run(self, run_id: int) -> List[Report]:
        stmt = select(Report).where(Report.run_id == run_id)
        return list(self._session.scalars(stmt).all())
