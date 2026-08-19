"""graph/tools/db_tools 单元测试。

覆盖 search_project / get_project_endpoints 的 Service 调用路径，
特别是按名称搜索无结果时的 fallback 分支（曾因参数缺漏抛 TypeError）。
"""

import json
from unittest.mock import MagicMock, patch


def _make_session_context() -> MagicMock:
    """构造 get_session() 上下文管理器 mock。"""
    session = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = session
    ctx.__exit__.return_value = False
    return ctx


class TestSearchProject:
    def test_search_fallback_when_no_match(self):
        """按名称搜索无结果时，fallback 查询启用项目且不抛异常。"""
        project = MagicMock()
        project.id = 1
        project.name = "demo"
        project.base_url = "http://example.com"
        project.description = "desc"

        service = MagicMock()
        service.list_projects.side_effect = [([], 0), ([project], 1)]

        ctx = _make_session_context()
        with (
            patch("src.graph.tools.db_tools.ensure_db"),
            patch("src.graph.tools.db_tools.get_db_manager") as mock_manager,
            patch("src.graph.tools.db_tools.ProjectService", return_value=service),
        ):
            mock_manager.return_value.get_session.return_value = ctx
            from src.graph.tools.db_tools import search_project

            result = search_project.invoke({"name": "不存在的项目"})

        assert service.list_projects.call_count == 2
        # fallback 调用必须是合法的四参数形式
        assert service.list_projects.call_args_list[1].args == (None, 1, 1, 100)
        data = json.loads(result)
        assert data == [{"id": 1, "name": "demo", "base_url": "http://example.com", "description": "desc"}]

    def test_search_returns_match_directly(self):
        """按名称直接命中时不再触发 fallback。"""
        project = MagicMock()
        project.id = 2
        project.name = "real"
        project.base_url = ""
        project.description = ""

        service = MagicMock()
        service.list_projects.return_value = ([project], 1)

        ctx = _make_session_context()
        with (
            patch("src.graph.tools.db_tools.ensure_db"),
            patch("src.graph.tools.db_tools.get_db_manager") as mock_manager,
            patch("src.graph.tools.db_tools.ProjectService", return_value=service),
        ):
            mock_manager.return_value.get_session.return_value = ctx
            from src.graph.tools.db_tools import search_project

            result = search_project.invoke({"name": "real"})

        service.list_projects.assert_called_once_with("real", None, 1, 100)
        assert json.loads(result)[0]["name"] == "real"


class TestGetProjectEndpoints:
    def test_returns_endpoints_via_service(self):
        """通过 EndpointService.list_active 返回接口 JSON。"""
        endpoint = MagicMock()
        endpoint.id = 10
        endpoint.name = "get_user"
        endpoint.path = "/users/{id}"
        endpoint.method = "GET"
        endpoint.summary = "查询用户"
        endpoint.tags = '["user"]'
        endpoint.responses = "[]"

        service = MagicMock()
        service.list_active.return_value = [endpoint]

        ctx = _make_session_context()
        with (
            patch("src.graph.tools.db_tools.ensure_db"),
            patch("src.graph.tools.db_tools.get_db_manager") as mock_manager,
            patch("src.graph.tools.db_tools.EndpointService", return_value=service),
        ):
            mock_manager.return_value.get_session.return_value = ctx
            from src.graph.tools.db_tools import get_project_endpoints

            result = get_project_endpoints.invoke({"project_id": 1})

        service.list_active.assert_called_once_with(1)
        data = json.loads(result)
        assert data[0]["path"] == "/users/{id}"
        assert data[0]["method"] == "GET"
