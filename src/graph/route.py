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
