from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models.report import Report
from src.data.repositories import ReportRepository

logger = get_logger(__name__)


class ReportService:
    def __init__(self, session: Session):
        self.repo = ReportRepository(session)

    def create_report(self, report: Report) -> Report:
        """创建报告记录"""
        logger.info(
            f"创建报告: run_id={report.run_id}, format={report.format}",
            action="create_report",
            run_id=report.run_id,
            format=report.format,
        )
        return self.repo.add(report)

    def get_reports_by_run(self, run_id: int) -> list[Report]:
        """获取某次执行的所有报告"""
        return self.repo.get_by_run(run_id)

    def get_report_by_format(self, run_id: int, report_format: str) -> Report | None:
        """获取某次执行指定格式的报告"""
        return self.repo.get_by_run_and_format(run_id, report_format)
