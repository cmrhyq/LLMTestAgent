"""条件边路由函数与路由注册表。

新增 intent / test_mode 时只改注册表，不改一长串 if。
"""

from src.graph.constants import NodeName, TestMode, UserIntent
from src.graph.state import AgentState

# 用户意图 → 下一跳节点
INTENT_ROUTES: dict[UserIntent, NodeName] = {
    UserIntent.PARSE_OPENAPI: NodeName.PARSE_OPENAPI_DOC,
    UserIntent.RUN_TEST: NodeName.SELECT_ENDPOINTS_AGENT,
}

# 测试模式 → 用例生成节点
TEST_MODE_ROUTES: dict[TestMode, NodeName] = {
    TestMode.SINGLE: NodeName.GENERATE_SINGLE_CASES,
    TestMode.FLOW: NodeName.GENERATE_FLOW_CASES,
}

# 生成用例成功后的下一跳（与 TEST_MODE_ROUTES 对应）
TEST_MODE_NEXT: dict[TestMode, NodeName] = {
    TestMode.SINGLE: NodeName.EXECUTE_SINGLE_TESTS,
    TestMode.FLOW: NodeName.EXECUTE_FLOW_TESTS,
}


def route_by_next_node(state: AgentState) -> str:
    """通用条件边路由：按 state.next_node 返回下一跳节点名。"""
    return state.get("next_node") or NodeName.ERROR.value


def route_by_intent(state: AgentState) -> str:
    """根据用户意图路由到对应节点。"""
    raw = state.get("user_intent", "")
    try:
        intent = UserIntent(raw)
    except ValueError:
        intent = UserIntent.RUN_TEST
    return INTENT_ROUTES.get(intent, NodeName.SELECT_ENDPOINTS_AGENT).value


def route_by_test_mode(state: AgentState) -> str:
    """根据测试模式路由到 single 或 flow 分支。"""
    raw = state.get("test_mode", "")
    try:
        test_mode = TestMode(raw)
    except ValueError:
        test_mode = TestMode.SINGLE
    return TEST_MODE_ROUTES.get(test_mode, NodeName.GENERATE_SINGLE_CASES).value
