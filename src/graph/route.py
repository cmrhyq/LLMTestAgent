from src.graph.state import TestGraphState


def route_by_intent(state: TestGraphState) -> str:
    """
    根据用户意图路由到对应节点。

    Args:
        state: 当前状态

    Returns:
        str: 下一个节点名称
    """
    intent = state.get("user_intent", "run_test")
    if intent == "parse_openapi":
        return "parse_openapi_doc"
    return "select_endpoints"