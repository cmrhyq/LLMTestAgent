import unittest

from src.core.models import APIInfo, HttpMethod, Priority
from src.services.case_generator import CaseGenerator
from src.services.llm_client import LLMClient


class _FailingLLMClient(LLMClient):
    def chat(self, messages, **kwargs) -> str:
        raise RuntimeError("upstream llm error")

    def get_model(self):
        return None


class _InvalidPayloadLLMClient(LLMClient):
    def chat(self, messages, **kwargs) -> str:
        return "not json"

    def get_model(self):
        return None


class _ValidLLMClient(LLMClient):
    def chat(self, messages, **kwargs) -> str:
        return """
{
  "test_cases": [
    {
      "case_name": "登录-正常场景",
      "scenario_type": "normal",
      "priority": "P0",
      "headers": {"Content-Type": "application/json"},
      "body": {"username": "u", "password": "p"},
      "assert_rules": ["$.code == 200"],
      "expected_result": "成功",
      "description": "LLM生成"
    }
  ]
}
"""

    def get_model(self):
        return None


class CaseGeneratorNoFallbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_info = APIInfo(
            name="登录",
            api_url="https://example.test/api/login",
            method=HttpMethod.POST,
            headers={"Content-Type": "application/json"},
            body={"username": "u", "password": "p"},
            assert_rules=["$.code == 200"],
            priority=Priority.P0,
        )

    def test_raise_when_llm_call_fails(self) -> None:
        generator = CaseGenerator(llm_client=_FailingLLMClient())
        with self.assertRaises(RuntimeError):
            generator.generate([self.api_info])

    def test_raise_when_llm_response_invalid(self) -> None:
        generator = CaseGenerator(llm_client=_InvalidPayloadLLMClient())
        with self.assertRaises(RuntimeError):
            generator.generate([self.api_info])

    def test_success_only_from_llm(self) -> None:
        generator = CaseGenerator(llm_client=_ValidLLMClient())
        cases = generator.generate([self.api_info])
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].case_name, "登录-正常场景")


if __name__ == "__main__":
    unittest.main()
