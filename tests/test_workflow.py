"""测试工作流集成测试。"""

import unittest
from pathlib import Path
from unittest.mock import patch

from src.workflow import TestWorkflow, build_graph


class TestBuildGraph(unittest.TestCase):
    """测试图的构建与编译。"""

    def test_build_graph_compiles_successfully(self):
        graph = build_graph()
        self.assertIsNotNone(graph)


class TestWorkflowIntegration(unittest.TestCase):
    """TestWorkflow 集成测试。"""

    @patch("src.graph.nodes.parse_input_node.get_llm_client")
    def test_parse_api_doc_workflow(self, mock_get_llm_client):
        mock_client = mock_get_llm_client.return_value
        mock_client.chat.return_value = '{"intent": "parse_openapi"}'

        api_doc_file_path = Path(__file__).parent.parent / "input" / "test.json"
        input_data = f"帮我解析API接口文档{api_doc_file_path}"

        workflow = TestWorkflow()
        result = workflow.run(
            raw_input=input_data,
            api_doc_file_path=api_doc_file_path,
        )
        self.assertIn("user_intent", result)

    @patch("src.graph.nodes.parse_input_node.get_llm_client")
    @patch("src.graph.nodes.select_endpoints_node.get_chat_model")
    def test_run_test_workflow(self, mock_get_model, mock_get_llm_client):
        mock_client = mock_get_llm_client.return_value
        mock_client.chat.return_value = '{"intent": "run_test"}'

        from unittest.mock import MagicMock
        from langchain_core.messages import AIMessage

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        final_response = AIMessage(
            content='{"selected_endpoint_ids": [1], "project_id": 1, '
            '"project_name": "test", "reason": "test"}'
        )
        mock_model.bind_tools.return_value.invoke.return_value = final_response

        workflow = TestWorkflow()
        result = workflow.run(raw_input="对用户模块执行测试")
        self.assertIn("user_intent", result)


if __name__ == "__main__":
    unittest.main()
