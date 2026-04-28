"""
LLM API自动化测试工具

基于LangChain+LangGraph框架开发的大模型API自动化测试工具
"""

__version__ = "1.0.0"
__author__ = "cmrhyq"

from src.data.enum.workflow import (
    APIInfo,
    Dependency,
    AssertRule,
    ValidationResult,
    WorkflowState,
)
from .core.config import get_config, init_config, AppConfig
from src.utils.parser.input_parser import InputParser, parse_input
from .graph.case_generator import CaseGenerator, generate_test_cases
from src.utils.excel.exporter import ExcelExporter, export_test_cases, export_test_results
from .graph.test_executor import TestExecutor, execute_tests
from .graph.report_generator import ReportGenerator, generate_report
try:
    from .workflows.workflow import TestWorkflow, run_workflow
except ImportError:
    TestWorkflow = None  # type: ignore[assignment]
    run_workflow = None  # type: ignore[assignment]
from src.core.llm.llm_client import LLMClient, create_llm_client, get_llm_client

__all__ = [
    # 数据模型
    "APIInfo",
    "Dependency",
    "AssertRule",
    "ValidationResult",
    "WorkflowState",
    # 配置
    "get_config",
    "init_config",
    "AppConfig",
    # 输入解析
    "InputParser",
    "parse_input",
    # 用例生成
    "CaseGenerator",
    "generate_test_cases",
    # Excel导出
    "ExcelExporter",
    "export_test_cases",
    "export_test_results",
    # 测试执行
    "TestExecutor",
    "execute_tests",
    # 报告生成
    "ReportGenerator",
    "generate_report",
    # 工作流
    "TestWorkflow",
    "run_workflow",
    # LLM客户端
    "LLMClient",
    "create_llm_client",
    "get_llm_client",
]
