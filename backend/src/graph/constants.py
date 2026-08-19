"""工作流层常量与枚举。

集中定义工作流专用的节点名、用户意图、测试模式枚举，
替换散落在 route.py / workflow.py / 各节点中的魔法字符串。
数据状态（``DataStatus`` 等）仍位于 ``src.data.enum.workflow``。
"""

from enum import Enum


class UserIntent(str, Enum):
    """用户意图。"""

    RUN_TEST = "run_test"  # 运行 API 测试
    PARSE_OPENAPI = "parse_openapi"  # 解析 OpenAPI 文档


class TestMode(str, Enum):
    """测试模式。"""

    SINGLE = "single"  # 单接口测试
    FLOW = "flow"  # 业务流程测试


class NodeName(str, Enum):
    """工作流图节点名。

    值即 LangGraph ``add_node`` / 条件边使用的字符串，保持与既有图结构一致。
    """

    START = "start"
    PARSE_INPUT = "parse_input"
    SELECT_ENDPOINTS_AGENT = "select_endpoints_agent"
    TOOLS = "tools"
    PARSE_RESULT = "parse_result"
    GENERATE_SINGLE_CASES = "generate_single_cases"
    EXECUTE_SINGLE_TESTS = "execute_single_tests"
    GENERATE_FLOW_CASES = "generate_flow_cases"
    EXECUTE_FLOW_TESTS = "execute_flow_tests"
    GENERATE_REPORT = "generate_report"
    PARSE_OPENAPI_DOC = "parse_openapi_doc"
    END = "end"
    ERROR = "error"
