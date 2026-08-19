"""测试工作流编排模块。

使用 LangGraph StateGraph 定义有状态工作流：
- parse_input: 意图解析
- select_endpoints: 接口挑选（Agent + ToolNode 循环）
- generate_single_cases: 单接口测试用例生成（LLM 驱动）
- generate_flow_cases: 流程测试用例生成（LLM 驱动）
- execute_single_tests: 单接口测试执行（HTTP 请求 + 断言）
- execute_flow_tests: 流程测试执行（顺序执行 + 上下文传递）
- generate_report: 报告生成
- parse_openapi_doc: OpenAPI 文档解析

节点名与路由统一使用 ``src.graph.constants`` 中的枚举，
条件边由 ``src.graph.route`` 的注册表驱动。
"""

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.core.config import AppConfig, get_config
from src.core.logging import get_logger
from src.data.enum.workflow import TestStatus
from src.graph.constants import NodeName
from src.graph.nodes.end_node import end_node
from src.graph.nodes.error_node import error_node
from src.graph.nodes.execute_flow_tests_node import execute_flow_tests_node
from src.graph.nodes.execute_single_tests_node import execute_single_tests_node
from src.graph.nodes.generate_flow_cases_node import generate_flow_cases_node
from src.graph.nodes.generate_report_node import generate_report_node
from src.graph.nodes.generate_single_cases_node import generate_single_cases_node
from src.graph.nodes.parse_input_node import parse_input_node
from src.graph.nodes.parse_openapi_node import parse_openapi_node
from src.graph.nodes.select_endpoints_node import (
    AVAILABLE_TOOLS,
    parse_endpoints_result_node,
    select_endpoints_agent_node,
)
from src.graph.nodes.start_node import start_node
from src.graph.route import route_by_intent, route_by_next_node, route_by_test_mode
from src.graph.state import AgentState

logger = get_logger(__name__)


def build_graph() -> CompiledStateGraph:
    """构建并编译测试工作流图。

    图结构:
        START -> parse_input -> (route_by_intent)
            -> "select_endpoints_agent" -> (tools_condition) -> tools -> (循环)
            -> (tools_condition) -> parse_result -> (route_by_test_mode)
                -> "generate_single_cases" -> execute_single_tests -> generate_report -> END
                -> "generate_flow_cases" -> execute_flow_tests -> generate_report -> END
            -> "parse_openapi_doc" -> END

    Returns:
        编译后的 StateGraph
    """
    workflow = StateGraph(AgentState)

    workflow.add_node(NodeName.START.value, start_node)
    workflow.add_node(NodeName.PARSE_INPUT.value, parse_input_node)
    # 测试分支公共节点
    workflow.add_node(NodeName.SELECT_ENDPOINTS_AGENT.value, select_endpoints_agent_node)
    workflow.add_node(NodeName.TOOLS.value, ToolNode(tools=AVAILABLE_TOOLS))
    workflow.add_node(NodeName.PARSE_RESULT.value, parse_endpoints_result_node)
    # 用例生成 / 执行节点
    workflow.add_node(NodeName.GENERATE_SINGLE_CASES.value, generate_single_cases_node)
    workflow.add_node(NodeName.EXECUTE_SINGLE_TESTS.value, execute_single_tests_node)
    workflow.add_node(NodeName.GENERATE_FLOW_CASES.value, generate_flow_cases_node)
    workflow.add_node(NodeName.EXECUTE_FLOW_TESTS.value, execute_flow_tests_node)
    # 公共报告节点
    workflow.add_node(NodeName.GENERATE_REPORT.value, generate_report_node)
    # 解析API文档分支
    workflow.add_node(NodeName.PARSE_OPENAPI_DOC.value, parse_openapi_node)
    # 结束和错误节点
    workflow.add_node(NodeName.END.value, end_node)
    workflow.add_node(NodeName.ERROR.value, error_node)

    workflow.add_edge(START, NodeName.START.value)
    workflow.add_conditional_edges(
        NodeName.START.value,
        route_by_next_node,
        {
            NodeName.PARSE_INPUT.value: NodeName.PARSE_INPUT.value,
            NodeName.ERROR.value: NodeName.ERROR.value,
        },
    )

    workflow.add_conditional_edges(
        NodeName.PARSE_INPUT.value,
        route_by_intent,
        {
            NodeName.SELECT_ENDPOINTS_AGENT.value: NodeName.SELECT_ENDPOINTS_AGENT.value,
            NodeName.PARSE_OPENAPI_DOC.value: NodeName.PARSE_OPENAPI_DOC.value,
        },
    )

    workflow.add_conditional_edges(
        NodeName.SELECT_ENDPOINTS_AGENT.value,
        tools_condition,
        {
            NodeName.TOOLS.value: NodeName.TOOLS.value,
            END: NodeName.PARSE_RESULT.value,
        },
    )
    workflow.add_edge(NodeName.TOOLS.value, NodeName.SELECT_ENDPOINTS_AGENT.value)

    workflow.add_conditional_edges(
        NodeName.PARSE_RESULT.value,
        route_by_test_mode,
        {
            NodeName.GENERATE_SINGLE_CASES.value: NodeName.GENERATE_SINGLE_CASES.value,
            NodeName.GENERATE_FLOW_CASES.value: NodeName.GENERATE_FLOW_CASES.value,
        },
    )

    # single / flow 分支：生成 → 执行 → 报告，错误统一走 error
    for generate_node, execute_node in (
        (NodeName.GENERATE_SINGLE_CASES, NodeName.EXECUTE_SINGLE_TESTS),
        (NodeName.GENERATE_FLOW_CASES, NodeName.EXECUTE_FLOW_TESTS),
    ):
        workflow.add_conditional_edges(
            generate_node.value,
            route_by_next_node,
            {
                execute_node.value: execute_node.value,
                NodeName.ERROR.value: NodeName.ERROR.value,
            },
        )
        workflow.add_conditional_edges(
            execute_node.value,
            route_by_next_node,
            {
                NodeName.GENERATE_REPORT.value: NodeName.GENERATE_REPORT.value,
                NodeName.ERROR.value: NodeName.ERROR.value,
            },
        )

    for terminal_node in (NodeName.GENERATE_REPORT, NodeName.PARSE_OPENAPI_DOC):
        workflow.add_conditional_edges(
            terminal_node.value,
            route_by_next_node,
            {
                NodeName.END.value: NodeName.END.value,
                NodeName.ERROR.value: NodeName.ERROR.value,
            },
        )

    # 结束节点连接到 END
    workflow.add_edge(NodeName.END.value, END)
    workflow.add_edge(NodeName.ERROR.value, END)

    return workflow.compile()


class TestWorkflow:
    """测试工作流入口类。

    提供 run() 方法运行完整的测试工作流。

    Attributes:
        config: 应用配置
        graph: 编译后的 LangGraph 图
    """

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()
        self.graph = build_graph()

    def run(
        self,
        raw_input: str,
        api_doc_file_path: Path | None = None,
    ) -> dict[str, Any]:
        """运行工作流。

        Args:
            raw_input: 用户自然语言指令
            api_doc_file_path: OpenAPI 文档文件路径

        Returns:
            最终工作流状态字典
        """
        logger.info(
            f"工作流开始执行，指令: {raw_input[:80]}，文档: {api_doc_file_path or '无'}",
            raw_input=raw_input,
            api_doc_file_path=str(api_doc_file_path) if api_doc_file_path else "",
        )

        initial_state: dict[str, Any] = {
            "raw_input": raw_input,
            "api_doc_file_path": str(api_doc_file_path) if api_doc_file_path else "",
            "next_node": "",
            "run_status": TestStatus.PENDING.value,
            "user_intent": "",
            "test_mode": "",
            "selected_endpoints": [],
            "endpoint_count": 0,
            "run_id": 0,
            "test_cases_count": 0,
            "test_results_summary": {},
            "report_path": "",
            "error_message": "",
            "audit_result": "",
            "messages": [],
        }

        try:
            final_state = self.graph.invoke(initial_state)
            logger.info(
                f"工作流执行完成，意图: {final_state.get('user_intent', '')}, "
                f"状态: {final_state.get('run_status', '')}",
                intent=final_state.get("user_intent", ""),
                run_status=final_state.get("run_status", ""),
            )
            return final_state
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}", error=str(e), raw_input=raw_input[:100])
            initial_state["error_message"] = str(e)
            initial_state["run_status"] = TestStatus.FAILED.value
            return initial_state
