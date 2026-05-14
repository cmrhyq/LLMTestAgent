"""条件边路由函数。"""

from src.graph.state import AgentState


def route_by_intent(state: AgentState) -> str:
    """根据用户意图路由到对应节点。

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    intent = state.get("user_intent", "run_test")
    if intent == "parse_openapi":
        return "parse_openapi_doc"
    return "select_endpoints"


def route_by_test_mode(state: AgentState) -> str:
    """根据测试模式路由到 single 或 flow 分支。

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    test_mode = state.get("test_mode", "single")
    if test_mode == "flow":
        return "generate_flow_cases"
    return "generate_single_cases"
