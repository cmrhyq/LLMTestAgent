from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models.test_summary import TestSummary
from src.data.repositories.base import BaseRepository


class TestSummaryRepository(BaseRepository[TestSummary]):
    """测试摘要表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestSummary, session)

    def get_by_run(self, run_id: int) -> TestSummary | None:
        stmt = select(TestSummary).where(TestSummary.run_id == run_id)
        return self._session.scalar(stmt)

    def create_or_update(
        self,
        run_id: int,
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        error: int,
        pass_rate: float,
        avg_response_time: float = 0.0,
        min_response_time: float = 0.0,
        max_response_time: float = 0.0,
        p95_response_time: float = 0.0,
        total_duration: float = 0.0,
        failure_reasons: str = "{}",
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> TestSummary:
        """创建或更新测试摘要"""
        existing = self.get_by_run(run_id)
        if existing:
            existing.total = total
            existing.passed = passed
            existing.failed = failed
            existing.skipped = skipped
            existing.error = error
            existing.pass_rate = pass_rate
            existing.avg_response_time = avg_response_time
            existing.min_response_time = min_response_time
            existing.max_response_time = max_response_time
            existing.p95_response_time = p95_response_time
            existing.total_duration = total_duration
            existing.failure_reasons = failure_reasons
            existing.started_at = started_at
            existing.finished_at = finished_at
            self._session.flush()
            return existing

        summary = TestSummary(
            run_id=run_id,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=pass_rate,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            total_duration=total_duration,
            failure_reasons=failure_reasons,
            started_at=started_at,
            finished_at=finished_at,
        )
        return self.add(summary)
