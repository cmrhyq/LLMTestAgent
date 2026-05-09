import json
import re
from typing import Any, Optional

from langgraph.graph.state import CompiledStateGraph

from src import AppConfig, get_config
from src.core.logging import get_logger
from src.core.llm.llm_client import get_llm_client
from src.graph.nodes.select_endpoints_node import select_endpoints_node
from src.graph.route import route_by_intent
from src.graph.state import TestGraphState
from src.prompts.builders.intent_builder import IntentPromptBuilder

try:
    from langgraph.graph import StateGraph, END

    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = Any  # type: ignore[assignment]
    END = "__END__"
    LANGGRAPH_AVAILABLE = False

logger = get_logger(__name__)


class TestWorkflow:
    """
    测试工作流

    基于LangGraph编排测试流程。

    Attributes:
        config: 应用配置
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
        self.graph = self.__build_graph()

    def run(self, raw_input: str) -> list[Any] | dict[str, Any] | TestGraphState | Any:
        """
        运行工作流

        Args:
            raw_input: 输入数据

        Returns:
            Dict[str, Any]: 工作流结果
        """
        logger.info("开始执行测试工作流")

        initial_state: TestGraphState = {
            "raw_input": raw_input,
            "user_intent": "",
            "selected_endpoints": [],
            "test_results": [],
            "test_summary": {},
            "report_path": "",
            "current_node": "parse_input",
            "error_message": "",
            "retry_count": 0,
            "should_continue": True,
        }

        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("测试工作流执行完成")
            return final_state
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            initial_state["error_message"] = str(e)
            initial_state["should_continue"] = False
            return initial_state

    #-----------------------------
    # 节点方法
    #-----------------------------

    def __build_graph(self) -> CompiledStateGraph[Any, Any, Any, Any]:
        """
        构建工作流图

        Returns:
            StateGraph: 工作流图
        """
        workflow = StateGraph(TestGraphState)

        workflow.add_node("parse_input", self._parse_input_node)
        workflow.add_node("select_endpoints", select_endpoints_node)
        workflow.add_node("generate_report", self._generate_report_node)
        workflow.add_node("parse_openapi_doc", self._parse_openapi_node)

        workflow.add_conditional_edges(
            "parse_input",
            route_by_intent,
            {
                "select_endpoints": "select_endpoints",
                "parse_openapi_doc": "parse_openapi_doc",
            },
        )
        workflow.add_edge("select_endpoints", "generate_report")
        workflow.add_edge("generate_report", END)
        workflow.add_edge("parse_openapi_doc", END)

        workflow.set_entry_point("parse_input")

        return workflow.compile()

    def _parse_input_node(self, state: TestGraphState) -> TestGraphState:
        """
        输入解析节点

        调用 LLM 判断用户意图：run_test 或 parse_openapi。

        Args:
            state: 当前状态

        Returns:
            TestGraphState: 更新后的状态
        """
        logger.info("进入输入解析节点")
        state["current_node"] = "parse_input"

        try:
            builder = IntentPromptBuilder()
            messages = builder.build_messages(state["raw_input"])

            llm_client = get_llm_client()
            response = llm_client.chat(messages)
            logger.info(f"LLM 意图分类响应: {response}")

            intent = self.__extract_intent(response)
            state["user_intent"] = intent
            logger.info(f"识别到用户意图: {intent}")
        except Exception as e:
            state["error_message"] = f"输入解析异常: {str(e)}"
            state["user_intent"] = "run_test"
            logger.error(f"{state['error_message']}，使用默认意图: run_test")

        return state

    def _parse_openapi_node(self, state: TestGraphState) -> TestGraphState:
        """
        OpenAPI 文档解析节点（占位）

        后续对接 api_doc_storage 模块实现完整解析逻辑。

        Args:
            state: 当前状态

        Returns:
            TestGraphState: 更新后的状态
        """
        logger.info("进入 OpenAPI 文档解析节点")
        state["current_node"] = "parse_openapi_doc"
        try:
            logger.info("OpenAPI 文档解析节点执行完成，等待后续对接 api_doc_storage 模块")
        except Exception as e:
            state["error_message"] = f"OpenAPI 文档解析异常: {str(e)}"
            logger.error(f"{state['error_message']}")

        return state

    def _generate_report_node(self, state: TestGraphState) -> TestGraphState:
        """
        报告生成节点

        Args:
            state: 当前状态

        Returns:
            TestGraphState: 更新后的状态
        """
        logger.info("进入报告生成节点")
        state["current_node"] = "generate_report"

        try:
            state["report_path"] = "a"

            logger.info(f"报告生成成功: {state["report_path"]}")

        except Exception as e:
            state["error_message"] = f"报告生成异常: {str(e)}"
            logger.error(state["error_message"])

        return state

    # -----------------------------
    # 内部方法
    # -----------------------------
    def __extract_intent(self, response: str) -> str:
        """
        从 LLM 响应中提取意图。

        优先使用 JSON 解析，失败时使用正则匹配作为后备。

        Args:
            response: LLM 原始响应文本

        Returns:
            str: 意图标识 ("run_test" 或 "parse_openapi")
        """
        valid_intents = ("run_test", "parse_openapi")

        try:
            data = json.loads(response.strip())
            intent = data.get("intent", "")
            if intent in valid_intents:
                return intent
        except (json.JSONDecodeError, AttributeError):
            pass

        match = re.search(r'"intent"\s*:\s*"(run_test|parse_openapi)"', response)
        if match:
            return match.group(1)

        return "run_test"