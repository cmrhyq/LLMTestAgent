"""
数据访问层（Repository 模式）

为每张表提供标准化的 CRUD 操作，所有数据库交互通过此模块进行。
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, TypeVar

from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import Session

from src.core.database.connection import Base
from src.data.models.models import (
    Project, Environment, ApiInfo, Tag, TestRun, TestCase, TestResult, AssertResult, TestSummary,
    ParamCache, Report, LlmInvocationLog, ExecutionLog,
)
from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class ProjectRepository(BaseRepository[Project]):
    """项目表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Project, session)

    def get_by_name(self, name: str) -> Optional[Project]:
        stmt = select(Project).where(Project.name == name)
        return self._session.scalar(stmt)

    def get_active_projects(self) -> List[Project]:
        stmt = select(Project).where(Project.is_active == 1)
        return list(self._session.scalars(stmt).all())

    def find_or_create(self, name: str, domain: str, description: str = "") -> Project:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        project = Project(name=name, domain=domain, description=description)
        return self.add(project)


class EnvironmentRepository(BaseRepository[Environment]):
    """环境表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Environment, session)

    def get_by_name(self, name: str) -> Optional[Environment]:
        stmt = select(Environment).where(Environment.name == name)
        return self._session.scalar(stmt)

    def get_active_environments(self) -> List[Environment]:
        stmt = select(Environment).where(Environment.is_active == 1)
        return list(self._session.scalars(stmt).all())

    def find_or_create(self, name: str, base_url: str, description: str = "") -> Environment:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        env = Environment(name=name, base_url=base_url, description=description)
        return self.add(env)


class ApiInfoRepository(BaseRepository[ApiInfo]):
    """API 定义表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(ApiInfo, session)

    def get_by_project(self, project_id: int, active_only: bool = True) -> List[ApiInfo]:
        conditions = [ApiInfo.project_id == project_id]
        if active_only:
            conditions.append(ApiInfo.is_active == 1)
        stmt = select(ApiInfo).where(and_(*conditions))
        return list(self._session.scalars(stmt).all())

    def get_by_api_id(self, project_id: int, api_id: str, version: int = 1) -> Optional[ApiInfo]:
        stmt = select(ApiInfo).where(
            and_(
                ApiInfo.project_id == project_id,
                ApiInfo.api_id == api_id,
                ApiInfo.version == version,
            )
        )
        return self._session.scalar(stmt)

    def get_by_method(self, project_id: int, method: str) -> List[ApiInfo]:
        stmt = select(ApiInfo).where(
            and_(ApiInfo.project_id == project_id, ApiInfo.method == method)
        )
        return list(self._session.scalars(stmt).all())


class TestRunRepository(BaseRepository[TestRun]):
    """执行批次表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestRun, session)

    def get_by_run_id(self, run_id: str) -> Optional[TestRun]:
        stmt = select(TestRun).where(TestRun.run_id == run_id)
        return self._session.scalar(stmt)

    def get_by_project(self, project_id: int, limit: int = 50) -> List[TestRun]:
        stmt = (
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .order_by(TestRun.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_by_status(self, status: str) -> List[TestRun]:
        stmt = select(TestRun).where(TestRun.status == status)
        return list(self._session.scalars(stmt).all())

    def update_status(self, run_db_id: int, status: str, error_message: str = "") -> None:
        values: Dict[str, Any] = {"status": status}
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


class TestCaseRepository(BaseRepository[TestCase]):
    """测试用例表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestCase, session)

    def get_by_run(self, run_id: int) -> List[TestCase]:
        stmt = select(TestCase).where(TestCase.run_id == run_id)
        return list(self._session.scalars(stmt).all())

    def get_by_case_id(self, case_id: str) -> Optional[TestCase]:
        stmt = select(TestCase).where(TestCase.case_id == case_id)
        return self._session.scalar(stmt)

    def get_by_scenario(self, run_id: int, scenario_type: str) -> List[TestCase]:
        stmt = select(TestCase).where(
            and_(TestCase.run_id == run_id, TestCase.scenario_type == scenario_type)
        )
        return list(self._session.scalars(stmt).all())

    def count_by_run(self, run_id: int) -> int:
        stmt = select(func.count()).select_from(TestCase).where(TestCase.run_id == run_id)
        return self._session.scalar(stmt) or 0


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


class AssertResultRepository(BaseRepository[AssertResult]):
    """断言结果表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(AssertResult, session)

    def get_by_test_result(self, test_result_id: int) -> List[AssertResult]:
        stmt = select(AssertResult).where(AssertResult.test_result_id == test_result_id)
        return list(self._session.scalars(stmt).all())

    def get_failed_assertions(self, test_result_id: int) -> List[AssertResult]:
        stmt = select(AssertResult).where(
            and_(AssertResult.test_result_id == test_result_id, AssertResult.passed == 0)
        )
        return list(self._session.scalars(stmt).all())


class TestSummaryRepository(BaseRepository[TestSummary]):
    """测试摘要表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(TestSummary, session)

    def get_by_run(self, run_id: int) -> Optional[TestSummary]:
        stmt = select(TestSummary).where(TestSummary.run_id == run_id)
        return self._session.scalar(stmt)


class ParamCacheRepository(BaseRepository[ParamCache]):
    """参数缓存表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(ParamCache, session)

    def get_by_run_and_key(self, run_id: int, cache_key: str) -> Optional[ParamCache]:
        stmt = select(ParamCache).where(
            and_(ParamCache.run_id == run_id, ParamCache.cache_key == cache_key)
        )
        return self._session.scalar(stmt)

    def upsert(self, run_id: int, cache_key: str, cache_value: str,
               source_api_id: str = "", source_path: str = "") -> ParamCache:
        existing = self.get_by_run_and_key(run_id, cache_key)
        if existing is not None:
            existing.cache_value = cache_value
            existing.source_api_id = source_api_id
            existing.source_path = source_path
            self._session.flush()
            return existing
        cache = ParamCache(
            run_id=run_id,
            cache_key=cache_key,
            cache_value=cache_value,
            source_api_id=source_api_id,
            source_path=source_path,
        )
        return self.add(cache)

    def get_all_by_run(self, run_id: int) -> List[ParamCache]:
        stmt = select(ParamCache).where(ParamCache.run_id == run_id)
        return list(self._session.scalars(stmt).all())


class ReportRepository(BaseRepository[Report]):
    """报告记录表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Report, session)

    def get_by_run(self, run_id: int) -> List[Report]:
        stmt = select(Report).where(Report.run_id == run_id)
        return list(self._session.scalars(stmt).all())


class LlmInvocationLogRepository(BaseRepository[LlmInvocationLog]):
    """LLM 调用日志表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(LlmInvocationLog, session)

    def get_by_run(self, run_id: int) -> List[LlmInvocationLog]:
        stmt = select(LlmInvocationLog).where(LlmInvocationLog.run_id == run_id)
        return list(self._session.scalars(stmt).all())

    def get_total_tokens_by_run(self, run_id: int) -> int:
        stmt = (
            select(func.sum(LlmInvocationLog.total_tokens))
            .where(LlmInvocationLog.run_id == run_id)
        )
        return self._session.scalar(stmt) or 0


class ExecutionLogRepository(BaseRepository[ExecutionLog]):
    """执行日志表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(ExecutionLog, session)

    def get_by_run(self, run_id: int, level: Optional[str] = None) -> List[ExecutionLog]:
        conditions = [ExecutionLog.run_id == run_id]
        if level is not None:
            conditions.append(ExecutionLog.level == level)
        stmt = (
            select(ExecutionLog)
            .where(and_(*conditions))
            .order_by(ExecutionLog.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def log(self, run_id: int, node_name: str, message: str,
            level: str = "INFO", extra_data: Optional[Dict[str, Any]] = None) -> ExecutionLog:
        entry = ExecutionLog(
            run_id=run_id,
            node_name=node_name,
            level=level,
            message=message,
            extra_data=json.dumps(extra_data or {}, ensure_ascii=False),
        )
        return self.add(entry)


class TagRepository(BaseRepository[Tag]):
    """标签表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Tag, session)

    def get_by_name(self, name: str) -> Optional[Tag]:
        stmt = select(Tag).where(Tag.name == name)
        return self._session.scalar(stmt)

    def find_or_create(self, name: str, color: str = "#6366f1") -> Tag:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        tag = Tag(name=name, color=color)
        return self.add(tag)
