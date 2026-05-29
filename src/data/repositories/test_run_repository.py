from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.data.models.test_run import TestRun
from src.data.repositories.base import BaseRepository


class TestRunRepository(BaseRepository[TestRun]):
    """执行批次表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestRun, session)

    def get_by_project(self, project_id: int, limit: int = 50) -> list[TestRun]:
        stmt = select(TestRun).where(TestRun.project_id == project_id).order_by(TestRun.created_at.desc()).limit(limit)
        return list(self._session.scalars(stmt).all())

    def get_by_status(self, status: str) -> list[TestRun]:
        stmt = select(TestRun).where(TestRun.status == status)
        return list(self._session.scalars(stmt).all())

    def update_status(self, run_db_id: int, status: str, error_message: str = "") -> None:
        values: dict[str, Any] = {"status": status}
        if status == "running":
            values["started_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        elif status in ("completed", "failed", "cancelled"):
            values["finished_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        if error_message:
            values["error_message"] = error_message
        stmt = update(TestRun).where(TestRun.id == run_db_id).values(**values)
        self._session.execute(stmt)
        self._session.flush()

    def update_statistics(
        self,
        run_db_id: int,
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        error: int,
        pass_rate: float,
        total_duration: float,
    ) -> None:
        stmt = (
            update(TestRun)
            .where(TestRun.id == run_db_id)
            .values(
                total_cases=total,
                passed_cases=passed,
                failed_cases=failed,
                skipped_cases=skipped,
                error_cases=error,
                pass_rate=pass_rate,
                total_duration=total_duration,
            )
        )
        self._session.execute(stmt)
        self._session.flush()
