from typing import Optional, List

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models.test_run import TestRun
from src.data.repositories import TestRunRepository

logger = get_logger(__name__)


class TestRunService:
    def __init__(self, session: Session):
        self.repo = TestRunRepository(session)

    def create_run(self, test_run: TestRun) -> TestRun:
        """创建执行批次"""
        logger.info(f"创建执行批次: {test_run.name}", action="create_run", name=test_run.name)
        return self.repo.add(test_run)

    def get_run(self, run_id: int) -> Optional[TestRun]:
        """获取执行批次"""
        return self.repo.get_by_id(run_id)

    def update_status(self, run_id: int, status: str, error_message: str = "") -> None:
        """更新执行状态"""
        logger.info(f"更新批次状态: run_id={run_id}, status={status}", action="update_status", run_id=run_id, status=status)
        self.repo.update_status(run_id, status, error_message)

    def update_statistics(
        self,
        run_id: int,
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        error: int,
        pass_rate: float,
        total_duration: float,
    ) -> None:
        """更新统计数据"""
        logger.info(
            f"更新批次统计: run_id={run_id}, total={total}, pass_rate={pass_rate:.2f}%",
            action="update_statistics", run_id=run_id, total=total, pass_rate=pass_rate,
        )
        self.repo.update_statistics(run_id, total, passed, failed, skipped, error, pass_rate, total_duration)

    def get_runs_by_project(self, project_id: int, limit: int = 50) -> List[TestRun]:
        """按项目获取执行批次列表"""
        return self.repo.get_by_project(project_id, limit)
