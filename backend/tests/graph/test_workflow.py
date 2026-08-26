"""工作流路由注册表与图编译测试。

阶段 3 验收：
- 注册表完整性：intent / test_mode 每个枚举值都有路由，且互不冲突
- build_graph() 可正常编译
- AgentState 无死字段（test_results / test_summary 已移除）
"""

from data.constant.constants import NodeName, UserIntent
from src.graph.route import INTENT_ROUTES, TEST_MODE_ROUTES, route_by_intent, route_by_next_node, route_by_test_mode
from src.workflow import build_graph


class TestRouteRegistries:
    """路由注册表完整性。"""

    def test_intent_routes_cover_all_intents(self):
        assert set(INTENT_ROUTES) == set(UserIntent)

    def test_test_mode_routes_cover_all_modes(self):
        from data.constant.constants import TestMode

        assert set(TEST_MODE_ROUTES) == set(TestMode)

    def test_intent_routes_are_distinct(self):
        values = [node.value for node in INTENT_ROUTES.values()]
        assert len(values) == len(set(values))

    def test_route_by_intent(self):
        assert route_by_intent({"user_intent": UserIntent.RUN.value}) == NodeName.SELECT_ENDPOINTS_AGENT.value
        assert route_by_intent({"user_intent": UserIntent.ASK.value}) == NodeName.ANSWER_QUESTION.value

    def test_route_by_test_mode(self):
        assert route_by_test_mode({"test_mode": "flow"}) == NodeName.GENERATE_FLOW_CASES.value
        assert route_by_test_mode({"test_mode": "single"}) == NodeName.GENERATE_SINGLE_CASES.value

    def test_route_falls_back_on_unknown(self):
        assert route_by_intent({"user_intent": "bogus"}) == NodeName.SELECT_ENDPOINTS_AGENT.value
        assert route_by_test_mode({"test_mode": "bogus"}) == NodeName.GENERATE_SINGLE_CASES.value


class TestRouteByNextNode:
    """通用 next_node 路由。"""

    def test_returns_next_node(self):
        assert route_by_next_node({"next_node": NodeName.GENERATE_REPORT.value}) == NodeName.GENERATE_REPORT.value

    def test_error_route(self):
        assert route_by_next_node({"next_node": NodeName.ERROR.value}) == NodeName.ERROR.value

    def test_missing_next_node_goes_error(self):
        assert route_by_next_node({}) == NodeName.ERROR.value


class TestBuildGraph:
    """工作流图编译。"""

    def test_graph_compiles(self):
        graph = build_graph()
        assert graph is not None

    def test_workflow_nodes_registered(self):
        graph = build_graph()
        nodes = set(graph.get_graph().nodes.keys())
        expected = {
            NodeName.START.value,
            NodeName.PARSE_INPUT.value,
            NodeName.SELECT_ENDPOINTS_AGENT.value,
            NodeName.TOOLS.value,
            NodeName.PARSE_RESULT.value,
            NodeName.GENERATE_SINGLE_CASES.value,
            NodeName.EXECUTE_SINGLE_TESTS.value,
            NodeName.GENERATE_FLOW_CASES.value,
            NodeName.EXECUTE_FLOW_TESTS.value,
            NodeName.GENERATE_REPORT.value,
            NodeName.ANSWER_QUESTION.value,
            NodeName.END.value,
            NodeName.ERROR.value,
        }
        assert expected.issubset(nodes)


class TestAgentState:
    """AgentState 字段契约：无死字段。"""

    def test_no_dead_fields(self):
        from src.graph.state import AgentState

        hints = set(AgentState.__annotations__)
        # 已删除的死字段不允许再出现
        assert "test_results" not in hints
        assert "test_summary" not in hints
        assert "current_step" not in hints
        assert "api_doc_file_path" not in hints
        # 关键字段必须存在
        assert {"next_node", "run_status", "selected_endpoints", "test_results_summary"}.issubset(hints)
