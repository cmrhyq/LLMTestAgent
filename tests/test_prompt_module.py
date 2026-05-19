import unittest


class TestPromptModule(unittest.TestCase):
    def test_loader_can_load_case_system_prompt(self):
        from src.prompts.loader import PromptLoader

        loader = PromptLoader()
        prompt = loader.load_simple_prompt_sync("single_case_system.yaml")
        self.assertIn("你是一个专业的测试用例专家", prompt)

    def test_case_builder_renders_user_prompt(self):
        from src.prompts.builders.case_builder import CasePromptBuilder

        builder = CasePromptBuilder()
        user_prompt = builder.build_user_prompt(
            {
                "name": "用户登录",
                "url": "https://api.example.com/login",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"username": "u", "password": "p"},
                "assert_rules": ["$.code == 200"],
                "priority": "P0",
                "description": "登录接口",
            },
            "- 正常场景 (normal)\n- 参数缺失场景 (param_missing)",
        )

        self.assertIn("API名称: 用户登录", user_prompt)
        self.assertIn("正常场景 (normal)", user_prompt)

    def test_intent_builder_builds_messages(self):
        from src.prompts.builders.intent_builder import IntentPromptBuilder

        builder = IntentPromptBuilder()
        messages = builder.build_messages("帮我测试用户登录接口")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("意图分类", messages[0]["content"])

    def test_flow_case_builder_builds_messages(self):
        from src.prompts.builders.flow_case_builder import FlowCasePromptBuilder

        builder = FlowCasePromptBuilder()
        endpoints_info = [{"endpoint_id": 1, "name": "登录", "method": "POST"}]
        messages = builder.build_messages(endpoints_info)
        self.assertEqual(len(messages), 2)
        self.assertIn("业务流程", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
