"""
SQLAlchemy ORM 模型定义

映射 sql/schema.sql 中的 14 张表到 Python ORM 模型。
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Integer, Text, Float, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base


def _local_now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


class Project(Base):
    """项目表 - 管理多个被测服务"""
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    api_infos: Mapped[List["ApiInfo"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_runs: Mapped[List["TestRun"]] = relationship(back_populates="project")

    __table_args__ = (
        Index("idx_project_name", "name"),
        Index("idx_project_active", "is_active"),
    )


class Environment(Base):
    """测试环境表"""
    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    variables: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_runs: Mapped[List["TestRun"]] = relationship(back_populates="environment")

    __table_args__ = (
        Index("idx_env_name", "name"),
        Index("idx_env_active", "is_active"),
    )


class ApiInfo(Base):
    """API 定义表"""
    __tablename__ = "api_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    api_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[str] = mapped_column(Text, default="{}")
    body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    params: Mapped[Optional[str]] = mapped_column(Text, default=None)
    cache_rules: Mapped[Optional[str]] = mapped_column(Text, default=None)
    assert_rules: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="P1")
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    project: Mapped["Project"] = relationship(back_populates="api_infos")
    dependencies: Mapped[List["ApiDependency"]] = relationship(back_populates="api_info", cascade="all, delete-orphan")
    api_tags: Mapped[List["ApiTag"]] = relationship(back_populates="api_info", cascade="all, delete-orphan")
    test_cases: Mapped[List["TestCase"]] = relationship(back_populates="api_info")

    __table_args__ = (
        CheckConstraint("method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')", name="ck_api_method"),
        CheckConstraint("priority IN ('P0','P1','P2')", name="ck_api_priority"),
        UniqueConstraint("project_id", "api_id", "version", name="uk_api_project_apiid_version"),
        Index("idx_api_project", "project_id"),
        Index("idx_api_api_id", "api_id"),
        Index("idx_api_method", "method"),
        Index("idx_api_priority", "priority"),
        Index("idx_api_active", "is_active"),
    )


class ApiDependency(Base):
    """API 依赖关系表"""
    __tablename__ = "api_dependency"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_info_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_info.id", ondelete="CASCADE"), nullable=False)
    source_api_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_param: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    api_info: Mapped["ApiInfo"] = relationship(back_populates="dependencies")

    __table_args__ = (
        Index("idx_dep_api_info", "api_info_id"),
        Index("idx_dep_source", "source_api_id"),
    )


class Tag(Base):
    """标签表"""
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    color: Mapped[str] = mapped_column(Text, default="#6366f1")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    api_tags: Mapped[List["ApiTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class ApiTag(Base):
    """API-标签关联表"""
    __tablename__ = "api_tag"

    api_info_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_info.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)

    api_info: Mapped["ApiInfo"] = relationship(back_populates="api_tags")
    tag: Mapped["Tag"] = relationship(back_populates="api_tags")


class TestRun(Base):
    """执行批次表"""
    __tablename__ = "test_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("project.id", ondelete="SET NULL"))
    environment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("environment.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    input_file: Mapped[str] = mapped_column(Text, default="")
    input_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    config_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    llm_provider: Mapped[str] = mapped_column(Text, default="")
    llm_model: Mapped[str] = mapped_column(Text, default="")
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    finished_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    total_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    project: Mapped[Optional["Project"]] = relationship(back_populates="test_runs")
    environment: Mapped[Optional["Environment"]] = relationship(back_populates="test_runs")
    test_cases: Mapped[List["TestCase"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")
    test_results: Mapped[List["TestResult"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")
    summary: Mapped[Optional["TestSummary"]] = relationship(back_populates="test_run", uselist=False, cascade="all, delete-orphan")
    param_caches: Mapped[List["ParamCache"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")
    llm_logs: Mapped[List["LlmInvocationLog"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")
    execution_logs: Mapped[List["ExecutionLog"]] = relationship(back_populates="test_run", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('pending','running','completed','failed','cancelled')", name="ck_run_status"),
        CheckConstraint("trigger_type IN ('manual','scheduled','ci')", name="ck_run_trigger"),
        Index("idx_run_project", "project_id"),
        Index("idx_run_env", "environment_id"),
        Index("idx_run_status", "status"),
        Index("idx_run_trigger", "trigger_type"),
        Index("idx_run_started", "started_at"),
        Index("idx_run_created", "created_at"),
    )


class TestCase(Base):
    """测试用例表"""
    __tablename__ = "test_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    api_info_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("api_info.id", ondelete="SET NULL"))
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_type: Mapped[str] = mapped_column(Text, nullable=False, default="normal")
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="P1")
    headers: Mapped[str] = mapped_column(Text, default="{}")
    body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    params: Mapped[Optional[str]] = mapped_column(Text, default=None)
    cache_rules: Mapped[Optional[str]] = mapped_column(Text, default=None)
    assert_rules: Mapped[str] = mapped_column(Text, default="[]")
    expected_result: Mapped[str] = mapped_column(Text, default="成功")
    description: Mapped[str] = mapped_column(Text, default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    unique_hash: Mapped[str] = mapped_column(Text, default="")
    generated_by: Mapped[str] = mapped_column(Text, nullable=False, default="llm")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="test_cases")
    api_info: Mapped[Optional["ApiInfo"]] = relationship(back_populates="test_cases")
    test_results: Mapped[List["TestResult"]] = relationship(back_populates="test_case", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("method IN ('GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS')", name="ck_case_method"),
        CheckConstraint(
            "scenario_type IN ('normal','param_missing','param_type_error','boundary_value','permission_error','custom')",
            name="ck_case_scenario",
        ),
        CheckConstraint("priority IN ('P0','P1','P2')", name="ck_case_priority"),
        CheckConstraint("generated_by IN ('llm','manual','import')", name="ck_case_generated"),
        Index("idx_case_run", "run_id"),
        Index("idx_case_api", "api_info_id"),
        Index("idx_case_case_id", "case_id"),
        Index("idx_case_scenario", "scenario_type"),
        Index("idx_case_priority", "priority"),
        Index("idx_case_hash", "unique_hash"),
        Index("idx_case_generated", "generated_by"),
        Index("idx_case_active", "is_active"),
    )


class TestResult(Base):
    """测试结果表"""
    __tablename__ = "test_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_case.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    request_url: Mapped[str] = mapped_column(Text, default="")
    request_method: Mapped[str] = mapped_column(Text, default="")
    request_headers: Mapped[str] = mapped_column(Text, default="{}")
    request_body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    query_params: Mapped[Optional[str]] = mapped_column(Text, default=None)
    response_status_code: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    response_headers: Mapped[str] = mapped_column(Text, default="{}")
    response_body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    finished_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="test_results")
    test_case: Mapped["TestCase"] = relationship(back_populates="test_results")
    assert_results: Mapped[List["AssertResult"]] = relationship(back_populates="test_result", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('pending','running','passed','failed','skipped','error')", name="ck_result_status"),
        Index("idx_result_run", "run_id"),
        Index("idx_result_case", "test_case_id"),
        Index("idx_result_status", "status"),
        Index("idx_result_resp_code", "response_status_code"),
        Index("idx_result_resp_time", "response_time"),
        Index("idx_result_started", "started_at"),
    )


class AssertResult(Base):
    """断言结果表"""
    __tablename__ = "assert_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_result.id", ondelete="CASCADE"), nullable=False)
    rule_expression: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, default="")
    operator: Mapped[str] = mapped_column(Text, default="")
    expected_value: Mapped[Optional[str]] = mapped_column(Text, default=None)
    actual_value: Mapped[Optional[str]] = mapped_column(Text, default=None)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_result: Mapped["TestResult"] = relationship(back_populates="assert_results")

    __table_args__ = (
        CheckConstraint(
            "operator IN ('==','!=','>','<','>=','<=','contains','not_contains','matches','exists','not_exists','')",
            name="ck_assert_operator",
        ),
        Index("idx_assert_result", "test_result_id"),
        Index("idx_assert_passed", "passed"),
    )


class TestSummary(Base):
    """测试摘要表"""
    __tablename__ = "test_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False, unique=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    min_response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_response_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    failure_reasons: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    finished_at: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="summary")

    __table_args__ = (
        Index("idx_summary_run", "run_id"),
        Index("idx_summary_pass_rate", "pass_rate"),
    )


class ParamCache(Base):
    """参数缓存表"""
    __tablename__ = "param_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    cache_key: Mapped[str] = mapped_column(Text, nullable=False)
    cache_value: Mapped[Optional[str]] = mapped_column(Text, default=None)
    source_api_id: Mapped[str] = mapped_column(Text, default="")
    source_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="param_caches")

    __table_args__ = (
        UniqueConstraint("run_id", "cache_key", name="uk_cache_run_key"),
        Index("idx_cache_run", "run_id"),
        Index("idx_cache_key", "cache_key"),
    )


class Report(Base):
    """报告记录表"""
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="reports")

    __table_args__ = (
        CheckConstraint("format IN ('excel','html','markdown','json')", name="ck_report_format"),
        Index("idx_report_run", "run_id"),
        Index("idx_report_format", "format"),
    )


class LlmInvocationLog(Base):
    """LLM 调用日志表"""
    __tablename__ = "llm_invocation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="case_generation")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    user_prompt: Mapped[str] = mapped_column(Text, default="")
    raw_response: Mapped[str] = mapped_column(Text, default="")
    is_success: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="llm_logs")

    __table_args__ = (
        CheckConstraint(
            "purpose IN ('case_generation','report_analysis','validation','other')",
            name="ck_llm_purpose",
        ),
        Index("idx_llm_run", "run_id"),
        Index("idx_llm_provider", "provider"),
        Index("idx_llm_purpose", "purpose"),
        Index("idx_llm_success", "is_success"),
        Index("idx_llm_created", "created_at"),
    )


class ExecutionLog(Base):
    """执行日志表"""
    __tablename__ = "execution_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_run.id", ondelete="CASCADE"), nullable=False)
    node_name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_local_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="execution_logs")

    __table_args__ = (
        CheckConstraint("level IN ('DEBUG','INFO','WARNING','ERROR')", name="ck_execlog_level"),
        Index("idx_execlog_run", "run_id"),
        Index("idx_execlog_node", "node_name"),
        Index("idx_execlog_level", "level"),
        Index("idx_execlog_created", "created_at"),
    )


def _update_timestamp(mapper, connection, target):
    """ORM 事件：更新 updated_at 时间戳"""
    if hasattr(target, "updated_at"):
        target.updated_at = _local_now()


for _model in (Project, Environment, ApiInfo, TestRun, TestCase):
    event.listen(_model, "before_update", _update_timestamp)
