"""测试工作流编排模块。

使用 LangGraph StateGraph 定义有状态工作流：
- parse_input: 意图解析
- select_endpoints: 接口挑选（Agent + ToolNode 循环）
- parse_openapi_doc: OpenAPI 文档解析
- generate_report: 报告生成
"""

from pathlib import Path
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.core.config import get_config, AppConfig
from src.core.logging import get_logger
from src.graph.nodes.generate_report_node import generate_report_node
from src.graph.nodes.parse_input_node import parse_input_node
from src.graph.nodes.parse_openapi_node import parse_openapi_node
from src.graph.nodes.select_endpoints_node import (
    AVAILABLE_TOOLS,
    parse_endpoints_result_node,
    select_endpoints_agent_node,
)
from src.graph.route import route_by_intent
from src.graph.state import AgentState

logger = get_logger(__name__)


def build_graph() -> CompiledStateGraph:
    """构建并编译测试工作流图。

    图结构:
        START -> parse_input -> (route_by_intent)
            -> "select_endpoints" -> select_endpoints_agent
                -> (tools_condition) -> tools -> select_endpoints_agent (循环)
                -> (tools_condition) -> parse_result -> generate_report -> END
            -> "parse_openapi_doc" -> parse_openapi_doc -> END

    Returns:
        编译后的 StateGraph
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("parse_input", parse_input_node)
    workflow.add_node("select_endpoints_agent", select_endpoints_agent_node)
    workflow.add_node("tools", ToolNode(tools=AVAILABLE_TOOLS))
    workflow.add_node("parse_result", parse_endpoints_result_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("parse_openapi_doc", parse_openapi_node)

    workflow.add_edge(START, "parse_input")

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

    workflow.add_edge("parse_result", "generate_report")
    workflow.add_edge("generate_report", END)
    workflow.add_edge("parse_openapi_doc", END)

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
            "user_intent": "",
            "selected_endpoints": [],
            "test_results": [],
            "test_summary": {},
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
