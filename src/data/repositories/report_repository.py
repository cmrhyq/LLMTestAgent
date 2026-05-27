from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from src.data.models.report import Report

from src.data.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    """报告记录表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Report, session)

    def get_by_run(self, run_id: int) -> List[Report]:
        stmt = select(Report).where(Report.run_id == run_id)
        return list(self._session.scalars(stmt).all())

    def get_by_run_and_format(self, run_id: int, format: str) -> Optional[Report]:
        stmt = select(Report).where(
            and_(Report.run_id == run_id, Report.format == format)
        )
        return self._session.scalar(stmt)
