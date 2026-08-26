"""SkillRunner 闭环测试：解析失败重试、校验失败降级、空结果 fallback。"""

import pytest

from src.graph.skill.base import ErrorHandlingSpec, Skill, ValidationSpec
from src.graph.skill.runner import SkillRunner, parse_full_json

VALID_CASES = '{"test_cases": [{"case_name": "正常", "priority": "P0", "assert_rules": ["status_code == 200"]}]}'
VALID_OBJECT = '{"security_analysis": {"risk_level": "none"}, "overall_verdict": {"action": "pass"}, "api_testing_analysis": {"is_api_testing": true}}'


class _FakeLLM:
    """可编排返回序列的假 LLM。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.message_history = []

    def chat(self, messages):
        self.calls += 1
        self.message_history.append(messages)
        return self.responses[min(self.calls - 1, len(self.responses) - 1)]


def _make_skill(validation=None, error_handling=None, user_prompt="接口: {url}"):
    return Skill(
        name="t",
        description="t",
        prompt="system",
        user_prompt=user_prompt,
        validation=validation,
        error_handling=error_handling or [],
    )


@pytest.mark.unit
class TestParseFullJson:
    """底层解析函数。"""

    def test_plain_json(self):
        data, ok = parse_full_json('{"a": 1}')
        assert ok is True and data == {"a": 1}

    def test_code_block_json(self):
        data, ok = parse_full_json('```json\n{"a": 1}\n```')
        assert ok is True and data == {"a": 1}

    def test_invalid_json(self):
        data, ok = parse_full_json("这不是JSON")
        assert ok is False and data is None

    def test_empty_response(self):
        assert parse_full_json("") == (None, False)


@pytest.mark.unit
class TestSkillRunner:
    """runner 的四种路径。"""

    def test_valid_output_no_retry(self):
        llm = _FakeLLM([VALID_CASES])
        spec = ValidationSpec(output_type="object", list_key="test_cases", item_required_fields=["case_name"])
        skill = _make_skill(spec, [ErrorHandlingSpec("parse_failure", "retry_with_feedback", max_retries=1)])
        result = SkillRunner(llm, skill).run({"url": "/x"})
        assert llm.calls == 1
        assert result.retries == 0
        assert result.errors == []
        assert result.final_data[0]["case_name"] == "正常"

    def test_parse_failure_then_retry_success(self):
        llm = _FakeLLM(["这不是JSON", VALID_CASES])
        spec = ValidationSpec(output_type="object", list_key="test_cases", item_required_fields=["case_name"])
        skill = _make_skill(spec, [ErrorHandlingSpec("parse_failure", "retry_with_feedback", max_retries=1)])
        result = SkillRunner(llm, skill).run({"url": "/x"})
        assert llm.calls == 2
        assert result.retries == 1
        assert result.final_data[0]["case_name"] == "正常"
        # 重试时反馈消息已追加
        assert "错误如下" in llm.message_history[1][-1]["content"]

    def test_parse_failure_exhausted_returns_none(self):
        llm = _FakeLLM(["坏", "坏", "坏"])
        skill = _make_skill(ValidationSpec(output_type="object", list_key="test_cases"),
                            [ErrorHandlingSpec("parse_failure", "retry_with_feedback", max_retries=1)])
        result = SkillRunner(llm, skill).run({"url": "/x"})
        assert llm.calls == 2  # 初始 + 1 次重试
        assert result.retries == 1
        assert result.final_data is None
        assert len(result.errors) == 1

    def test_validation_failure_fallback(self):
        llm = _FakeLLM(['{"security_analysis": {"risk_level": "wrong"}, "overall_verdict": {"action": "block"}}'])
        spec = ValidationSpec(output_type="object", custom_validators=["validate_risk_level"])
        skill = _make_skill(
            spec,
            [ErrorHandlingSpec("validation_failure", "fallback", fallback_value={"overall_verdict": {"action": "review"}})],
        )
        result = SkillRunner(llm, skill).run("input")
        assert result.final_data == {"overall_verdict": {"action": "review"}}
        assert len(result.errors) == 1

    def test_empty_result_fallback(self):
        llm = _FakeLLM(['{"test_cases": []}'])
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        skill = _make_skill(spec, [ErrorHandlingSpec("empty_result", "fallback", fallback_value=[])])
        result = SkillRunner(llm, skill).run({"url": "/x"})
        assert result.final_data == []

    def test_without_validation_passthrough(self):
        llm = _FakeLLM([VALID_CASES])
        skill = _make_skill(None, [])
        result = SkillRunner(llm, skill).run({"url": "/x"})
        # 无 validation 时直接返回解析后的完整对象
        assert result.final_data["test_cases"][0]["case_name"] == "正常"
        assert result.retries == 0

    def test_feedback_template_uses_errors(self):
        llm = _FakeLLM(["坏", VALID_CASES])
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        skill = _make_skill(
            spec,
            [ErrorHandlingSpec("parse_failure", "retry_with_feedback", max_retries=1, feedback_template="请修正: {errors}")],
        )
        SkillRunner(llm, skill).run({"url": "/x"})
        feedback = llm.message_history[1][-1]["content"]
        assert feedback.startswith("请修正: [")
        assert "输出不是有效的 JSON" in feedback
