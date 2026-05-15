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
"""

from pathlib import Path
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.core.config import get_config, AppConfig
from src.core.logging import get_logger
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
from src.graph.route import route_by_intent, route_by_test_mode, route_by_step
from src.graph.state import AgentState

logger = get_logger(__name__)


def build_graph() -> CompiledStateGraph:
    """构建并编译测试工作流图。

    图结构:
        START -> parse_input -> (route_by_intent)
            -> "select_endpoints" -> select_endpoints_agent
                -> (tools_condition) -> tools -> select_endpoints_agent (循环)
                -> (tools_condition) -> parse_result -> (route_by_test_mode)
                    -> "generate_single_cases" -> execute_single_tests -> generate_report -> END
                    -> "generate_flow_cases" -> execute_flow_tests -> generate_report -> END
            -> "parse_openapi_doc" -> parse_openapi_doc -> END

    Returns:
        编译后的 StateGraph
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("start", start_node)
    workflow.add_node("parse_input", parse_input_node)
    # 测试分支公共节点
    workflow.add_node("select_endpoints_agent", select_endpoints_agent_node)
    workflow.add_node("tools", ToolNode(tools=AVAILABLE_TOOLS))
    workflow.add_node("parse_result", parse_endpoints_result_node)
    # single 分支节点
    workflow.add_node("generate_single_cases", generate_single_cases_node)
    workflow.add_node("execute_single_tests", execute_single_tests_node)
    # flow 分支节点
    workflow.add_node("generate_flow_cases", generate_flow_cases_node)
    workflow.add_node("execute_flow_tests", execute_flow_tests_node)
    # 公共报告节点
    workflow.add_node("generate_report", generate_report_node)
    # 解析API文档分支
    workflow.add_node("parse_openapi_doc", parse_openapi_node)
    # 结束和错误节点
    workflow.add_node("end", end_node)
    workflow.add_node("error", error_node)


    workflow.add_edge(START, "start")
    workflow.add_conditional_edges(
        "start",
        route_by_step,
        {
            "parse_input": "parse_input",
            "error": "error"
        }
    )

    workflow.add_conditional_edges(
        "parse_input",
        route_by_intent,
        {
            "select_endpoints": "select_endpoints_agent",
            "parse_openapi_doc": "parse_openapi_doc",
        },
    )

    workflow.add_conditional_edges(
        "select_endpoints_agent",
        tools_condition,
        {
            "tools": "tools",
            END: "parse_result",
        },
    )
    workflow.add_edge("tools", "select_endpoints_agent")

    workflow.add_conditional_edges(
        "parse_result",
        route_by_test_mode,
        {
            "generate_single_cases": "generate_single_cases",
            "generate_flow_cases": "generate_flow_cases",
        },
    )

    # single 分支
    workflow.add_conditional_edges(
        "generate_single_cases",
        route_by_step,
        {
            "execute_single_tests": "execute_single_tests",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "execute_single_tests",
        route_by_step,
        {
            "generate_report": "generate_report",
            "error": "error"
        }
    )

    # flow 分支
    workflow.add_conditional_edges(
        "generate_flow_cases",
        route_by_step,
        {
            "execute_flow_tests": "execute_flow_tests",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "execute_flow_tests",
        route_by_step,
        {
            "generate_report": "generate_report",
            "error": "error"
        }
    )

    workflow.add_conditional_edges(
        "generate_report",
        route_by_step,
        {
            "end": "end",
            "error": "error"
        }
    )
    workflow.add_conditional_edges(
        "parse_openapi_doc",
        route_by_step,
        {
            "end": "end",
            "error": "error"
        }
    )

    # 结束节点连接到 END
    workflow.add_edge("end", END)
    workflow.add_edge("error", END)

    return workflow.compile()


class TestWorkflow:
    """测试工作流入口类。

    提供 run() 方法运行完整的测试工作流。

    Attributes:
        config: 应用配置
        graph: 编译后的 LangGraph 图
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.graph = build_graph()

    def run(
        self,
        raw_input: str,
        api_doc_file_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """运行工作流。

        Args:
            raw_input: 用户自然语言指令
            api_doc_file_path: OpenAPI 文档文件路径

        Returns:
            最终工作流状态字典
        """
        logger.info("开始执行测试工作流")

        initial_state: Dict[str, Any] = {
            "raw_input": raw_input,
            "api_doc_file_path": str(api_doc_file_path) if api_doc_file_path else "",
            "current_step": "",
            "user_intent": "",
            "test_mode": "",
            "selected_endpoints": [],
            "test_results": [],
            "test_summary": {},
            "run_id": 0,
            "test_cases_count": 0,
            "test_results_summary": {},
            "report_path": "",
            "error_message": "",
            "messages": [],
        }

        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("测试工作流执行完成")
            return final_state
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            initial_state["error_message"] = str(e)
            return initial_state
