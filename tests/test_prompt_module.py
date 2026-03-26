import unittest


class TestPromptModule(unittest.TestCase):
    def test_loader_can_load_case_system_prompt(self):
        from src.prompts.loader import PromptLoader

        loader = PromptLoader()
        prompt = loader.load_simple_prompt_sync("case_system.yaml")
        self.assertIn("你是一个专业的测试用例专家", prompt)

    def test_case_builder_renders_user_prompt(self):
        from src.prompts.builders.case_builder import CasePromptBuilder

        builder = CasePromptBuilder()
        user_prompt = builder.build_user_prompt(
            {
                "name": "用户登录",
                "api_url": "https://api.example.com/login",
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

    def test_case_module_keeps_backward_compatible_constants(self):
        from src.prompts.case import (
            CASE_GENERATION_SYSTEM_PROMPT,
            CASE_GENERATION_USER_PROMPT_TEMPLATE,
        )

        self.assertIn("测试用例专家", CASE_GENERATION_SYSTEM_PROMPT)
        self.assertIn("API名称: {name}", CASE_GENERATION_USER_PROMPT_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
