"""
LangGraph工作流编排模块

使用LangGraph StateGraph定义有状态工作流：
- 输入解析节点
- 用例生成节点
- 用例校验节点
- Excel导出节点
- 测试执行节点
- 报告生成节点

支持：
- 节点失败重试
- 人工确认节点（可选）
- 上下文管理
"""

from typing import Dict, Any, Optional, Literal

from langgraph.graph.state import CompiledStateGraph

from src.core.logging import get_logger
from ..graph.state import GraphState

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = Any  # type: ignore[assignment]
    END = "__END__"
    LANGGRAPH_AVAILABLE = False

from ..core.models import (
    APIInfo,
    TestCase,
    TestResult,
    TestSummary,
)
from ..core.config import get_config, AppConfig
from src.utils.parser.input_parser import InputParser
from ..graph.case_generator import CaseGenerator
from src.utils.excel.exporter import ExcelExporter
from ..graph.test_executor import TestExecutor
from ..graph.report_generator import ReportGenerator

logger = get_logger(__name__)


class TestWorkflow:
    """
    测试工作流
    
    基于LangGraph编排测试流程。
    
    Attributes:
        config: 应用配置
        graph: LangGraph图
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        初始化测试工作流
        
        Args:
            config: 应用配置
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "langgraph 或 langchain-core 版本不兼容，无法使用 TestWorkflow。"
            )

        self.config = config or get_config()
        self.graph = self._build_graph()
        
        # 组件实例
        self.input_parser = InputParser()
        self.case_generator = CaseGenerator(self.config)
        self.excel_exporter = ExcelExporter(self.config)
        self.test_executor = TestExecutor(self.config)
        self.report_generator = ReportGenerator(self.config)
    
    def _build_graph(self) -> CompiledStateGraph[Any, Any, Any, Any]:
        """
        构建工作流图
        
        Returns:
            StateGraph: 工作流图
        """
        # 创建图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("parse_input", self._parse_input_node)
        workflow.add_node("generate_cases", self._generate_cases_node)
        workflow.add_node("validate_cases", self._validate_cases_node)
        workflow.add_node("export_excel", self._export_excel_node)
        workflow.add_node("execute_tests", self._execute_tests_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # 添加边
        workflow.add_edge("parse_input", "generate_cases")
        workflow.add_conditional_edges(
            "generate_cases",
            self._should_validate,
            {
                "validate": "validate_cases",
                "skip": "export_excel",
            }
        )
        workflow.add_conditional_edges(
            "validate_cases",
            self._validation_result,
            {
                "pass": "export_excel",
                "retry": "generate_cases",
                "fail": END,
            }
        )
        workflow.add_edge("export_excel", "execute_tests")
        workflow.add_edge("execute_tests", "generate_report")
        workflow.add_edge("generate_report", END)
        
        # 设置入口
        workflow.set_entry_point("parse_input")
        
        return workflow.compile()
    
    def run(self, input_data: Dict[str, Any]) -> list[Any] | dict[str, Any] | GraphState | Any:
        """
        运行工作流
        
        Args:
            input_data: 输入数据
            
        Returns:
            Dict[str, Any]: 工作流结果
        """
        logger.info("开始执行测试工作流")
        
        # 初始状态
        initial_state: GraphState = {
            "raw_input": input_data,
            "api_infos": [],
            "validation_result": {},
            "test_cases": [],
            "execution_context": {},
            "test_results": [],
            "test_summary": {},
            "report_paths": {},
            "excel_path": "",
            "current_node": "parse_input",
            "error_message": "",
            "retry_count": 0,
            "should_continue": True,
        }
        
        # 执行工作流
        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("测试工作流执行完成")
            return final_state
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            initial_state["error_message"] = str(e)
            initial_state["should_continue"] = False
            return initial_state
    
    def _parse_input_node(self, state: GraphState) -> GraphState:
        """
        输入解析节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("📥 执行输入解析节点")
        state["current_node"] = "parse_input"
        
        try:
            api_infos, validation_result = self.input_parser.parse(state["raw_input"])
            
            # 转换为可序列化的格式
            state["api_infos"] = [api.model_dump() for api in api_infos]
            state["validation_result"] = validation_result.model_dump()
            
            if not validation_result.is_valid:
                state["error_message"] = f"输入校验失败: {validation_result.errors}"
                logger.error(state["error_message"])
            else:
                logger.info(f"输入解析成功: {len(api_infos)}个API")
                
        except Exception as e:
            state["error_message"] = f"输入解析异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _generate_cases_node(self, state: GraphState) -> GraphState:
        """
        用例生成节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("🔧 执行用例生成节点")
        state["current_node"] = "generate_cases"
        
        try:
            # 恢复API信息对象
            api_infos = [APIInfo(**api_data) for api_data in state["api_infos"]]
            
            # 生成用例
            test_cases = self.case_generator.generate(api_infos)
            
            # 转换为可序列化的格式
            state["test_cases"] = [case.model_dump() for case in test_cases]
            
            logger.info(f"用例生成成功: {len(test_cases)}个用例")
            
        except Exception as e:
            state["error_message"] = f"用例生成异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _validate_cases_node(self, state: GraphState) -> GraphState:
        """
        用例校验节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("✅ 执行用例校验节点")
        state["current_node"] = "validate_cases"
        
        try:
            # 恢复用例对象
            test_cases = [TestCase(**case_data) for case_data in state["test_cases"]]
            
            # 校验用例
            valid_cases = self.case_generator.validate_cases(test_cases)
            
            # 更新状态
            state["test_cases"] = [case.model_dump() for case in valid_cases]
            
            if len(valid_cases) < len(test_cases):
                invalid_count = len(test_cases) - len(valid_cases)
                logger.warning(f"校验过滤了{invalid_count}个无效用例")
            
            logger.info(f"用例校验完成: {len(valid_cases)}个有效用例")
            
        except Exception as e:
            state["error_message"] = f"用例校验异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _export_excel_node(self, state: GraphState) -> GraphState:
        """
        Excel导出节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("📊 执行Excel导出节点")
        state["current_node"] = "export_excel"
        
        try:
            # 恢复用例对象
            test_cases = [TestCase(**case_data) for case_data in state["test_cases"]]
            
            # 导出Excel
            excel_path = self.excel_exporter.export_test_cases(test_cases)
            state["excel_path"] = excel_path
            
            logger.info(f"Excel导出成功: {excel_path}")
            
        except Exception as e:
            state["error_message"] = f"Excel导出异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _execute_tests_node(self, state: GraphState) -> GraphState:
        """
        测试执行节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("🚀 执行测试执行节点")
        state["current_node"] = "execute_tests"
        
        try:
            # 恢复用例对象
            test_cases = [TestCase(**case_data) for case_data in state["test_cases"]]
            
            # 执行测试
            test_results = self.test_executor.execute(test_cases)
            
            # 生成摘要
            # TODO 可以喂给大模型生成一句话的摘要
            test_summary = TestSummary.from_results(test_results)
            
            # 转换为可序列化的格式
            state["test_results"] = [result.model_dump() for result in test_results]
            state["test_summary"] = test_summary.model_dump()
            
            logger.info(
                f"测试执行完成: 总计{test_summary.total}个, "
                f"通过{test_summary.passed}个, "
                f"失败{test_summary.failed}个, "
                f"通过率{test_summary.pass_rate}%"
            )
            
        except Exception as e:
            state["error_message"] = f"测试执行异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _generate_report_node(self, state: GraphState) -> GraphState:
        """
        报告生成节点
        
        Args:
            state: 当前状态
            
        Returns:
            GraphState: 更新后的状态
        """
        logger.info("📝 执行报告生成节点")
        state["current_node"] = "generate_report"
        
        try:
            # 恢复结果对象
            test_results = [TestResult(**result_data) for result_data in state["test_results"]]
            
            # 生成报告
            report_paths = self.report_generator.generate(test_results)
            state["report_paths"] = report_paths
            
            logger.info(f"报告生成成功: {report_paths}")
            
        except Exception as e:
            state["error_message"] = f"报告生成异常: {str(e)}"
            logger.error(state["error_message"])
        
        return state
    
    def _should_validate(self, state: GraphState) -> Literal["validate", "skip"]:
        """
        判断是否需要校验
        
        Args:
            state: 当前状态
            
        Returns:
            str: 下一个节点
        """
        # 如果配置了人工确认，则进行校验
        if self.config.case_generation.human_confirm:
            return "validate"
        
        # 如果有用例，进行校验
        if state["test_cases"]:
            return "validate"
        
        return "skip"
    
    def _validation_result(self, state: GraphState) -> Literal["pass", "retry", "fail"]:
        """
        判断校验结果
        
        Args:
            state: 当前状态
            
        Returns:
            str: 下一个节点
        """
        # 如果有错误且重试次数未超限，则重试
        if state["error_message"] and state["retry_count"] < 2:
            state["retry_count"] += 1
            logger.warning(f"校验失败，重试第{state['retry_count']}次")
            return "retry"
        
        # 如果有用例，则通过
        if state["test_cases"]:
            return "pass"
        
        # 否则失败
        return "fail"


def run_workflow(
    input_data: Dict[str, Any],
    config: Optional[AppConfig] = None
) -> Dict[str, Any]:
    """
    运行工作流的便捷函数
    
    Args:
        input_data: 输入数据
        config: 应用配置
        
    Returns:
        Dict[str, Any]: 工作流结果
    """
    workflow = TestWorkflow(config)
    return workflow.run(input_data)
