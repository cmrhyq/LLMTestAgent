from typing import List

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models.test_result import TestResult
from src.data.repositories import TestResultRepository

logger = get_logger(__name__)


class TestResultService:
    def __init__(self, session: Session):
        self.repo = TestResultRepository(session)

    def get_results_by_run(self, run_id: int) -> List[TestResult]:
        """获取某次执行的所有结果"""
        return self.repo.get_by_run(run_id)

    def get_failed_results(self, run_id: int) -> List[TestResult]:
        """获取某次执行中的失败/错误结果"""
        return self.repo.get_failed_results(run_id)

    def get_results_by_case(self, test_case_id: int) -> List[TestResult]:
        """获取某用例的所有执行结果"""
        return self.repo.get_by_test_case(test_case_id)

    def count_by_run(self, run_id: int) -> int:
        """统计某次执行的结果数"""
        return self.repo.count_by_run(run_id)
