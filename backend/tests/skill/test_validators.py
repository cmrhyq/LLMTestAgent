"""校验器测试：合法样例零错误、非法样例返回对应 ValidationError。"""

import pytest

from src.graph.skill.base import FieldRule, ValidationSpec
from src.graph.skill.validators import (
    ValidationError,
    run_validations,
    validate_assert_rules_syntax,
    validate_cache_rules,
    validate_complexity_level,
    validate_endpoint_ids,
    validate_risk_level,
)


@pytest.mark.unit
class TestAssertRulesSyntax:
    """断言语法校验（对齐 assertion_engine）。"""

    def test_valid_rules_zero_errors(self):
        rules = [
            "$.code == 200",
            "status_code == 200",
            "response_time < 3000",
            "$.message contains \"成功\"",
            "$.data.token exists",
            "$.data.token not_exists",
            "$.data.name matches \"^user_\\d+$\"",
            "$.data.count >= 1",
        ]
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        data = {"test_cases": [{"assert_rules": rules}]}
        assert validate_assert_rules_syntax(data, spec) == []

    def test_invalid_rules_return_errors(self):
        bad_rules = ["status_code ==", "foo bar", "", "$.code === 200"]
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        data = {"test_cases": [{"assert_rules": bad_rules}]}
        errors = validate_assert_rules_syntax(data, spec)
        assert len(errors) == 4
        for error in errors:
            assert isinstance(error, ValidationError)
            assert "assert_rules" in (error.field or "")

    def test_missing_path_operator_invalid(self):
        errors = validate_assert_rules_syntax({"assert_rules": ["200"]}, ValidationSpec(output_type="object"))
        assert len(errors) == 1


@pytest.mark.unit
class TestCacheRules:
    """cache_rules 结构校验。"""

    def _flow(self, cache_rules, step_order=None):
        item = {"cache_rules": cache_rules}
        if step_order is not None:
            item["step_order"] = step_order
        return {"test_cases": [item]}

    def test_valid_cache_rules(self):
        data = self._flow({"inject": [], "extract": [{"source_path": "$.data.token", "cache_key": "auth_token"}]})
        assert validate_cache_rules(data, ValidationSpec(output_type="object", list_key="test_cases")) == []

    def test_extract_missing_source_path(self):
        data = self._flow({"inject": [], "extract": [{"cache_key": "auth_token"}]})
        errors = validate_cache_rules(data, ValidationSpec(output_type="object", list_key="test_cases"))
        assert len(errors) == 1
        assert "source_path" in errors[0].message

    def test_inject_missing_target(self):
        data = self._flow({"inject": [{"cache_key": "auth_token"}], "extract": []})
        errors = validate_cache_rules(data, ValidationSpec(output_type="object", list_key="test_cases"))
        assert len(errors) == 1
        assert "target" in errors[0].message

    def test_first_step_inject_should_be_empty(self):
        data = {
            "test_cases": [
                {"step_order": 1, "cache_rules": {"inject": [{"cache_key": "x", "target": "headers.A"}], "extract": []}},
                {"step_order": 2, "cache_rules": {"inject": [], "extract": []}},
            ]
        }
        errors = validate_cache_rules(data, ValidationSpec(output_type="object", list_key="test_cases"))
        assert any("第一个步骤" in e.message for e in errors)


@pytest.mark.unit
class TestEndpointIds:
    """endpoint_id 上下文校验。"""

    def test_valid_ids_pass(self):
        data = {"test_cases": [{"endpoint_id": 1}, {"endpoint_id": 2}]}
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        assert validate_endpoint_ids(data, spec, {"valid_endpoint_ids": [1, 2]}) == []

    def test_invalid_id_flagged(self):
        data = {"test_cases": [{"endpoint_id": 99}]}
        spec = ValidationSpec(output_type="object", list_key="test_cases")
        errors = validate_endpoint_ids(data, spec, {"valid_endpoint_ids": [1, 2]})
        assert len(errors) == 1
        assert errors[0].value == 99

    def test_without_context_skips(self):
        data = {"test_cases": [{"endpoint_id": 99}]}
        assert validate_endpoint_ids(data, ValidationSpec(output_type="object", list_key="test_cases")) == []


@pytest.mark.unit
class TestRiskAndComplexity:
    """安全审计与复杂度分级校验。"""

    def test_valid_risk_level(self):
        data = {
            "security_analysis": {"is_safe": True, "risk_level": "none"},
            "overall_verdict": {"action": "pass"},
        }
        assert validate_risk_level(data, ValidationSpec(output_type="object")) == []

    def test_invalid_risk_level(self):
        data = {"security_analysis": {"risk_level": "extreme"}, "overall_verdict": {"action": "block"}}
        errors = validate_risk_level(data, ValidationSpec(output_type="object"))
        assert any("risk_level" in (e.field or "") for e in errors)

    def test_invalid_verdict_action(self):
        data = {"security_analysis": {"risk_level": "none"}, "overall_verdict": {"action": "maybe"}}
        errors = validate_risk_level(data, ValidationSpec(output_type="object"))
        assert any("action" in (e.field or "") for e in errors)

    def test_valid_complexity(self):
        data = {
            "scores": {"reasoning_depth": 3, "domain_knowledge": 2, "output_complexity": 3,
                       "context_dependency": 2, "precision_requirement": 3},
            "weighted_score": 2.7,
            "complexity_level": "moderate",
            "selected_model": "us.anthropic.claude-sonnet-4-6",
        }
        assert validate_complexity_level(data, ValidationSpec(output_type="object")) == []

    def test_invalid_complexity(self):
        data = {
            "scores": {"reasoning_depth": 9},
            "complexity_level": "ultra",
            "selected_model": "unknown-model",
        }
        errors = validate_complexity_level(data, ValidationSpec(output_type="object"))
        assert any("complexity_level" in (e.field or "") for e in errors)
        assert any("selected_model" in (e.field or "") for e in errors)
        assert any("scores.reasoning_depth" in (e.field or "") for e in errors)


@pytest.mark.unit
class TestFieldRulesAndDispatch:
    """字段规则与 run_validations 分发。"""

    def test_enum_rule(self):
        spec = ValidationSpec(
            output_type="object",
            list_key="test_cases",
            field_rules=[FieldRule(field="priority", type="enum", values=["P0", "P1", "P2"])],
        )
        good = {"test_cases": [{"priority": "P0"}]}
        bad = {"test_cases": [{"priority": "P9"}]}
        assert run_validations(good, spec) == []
        errors = run_validations(bad, spec)
        assert len(errors) == 1 and "P9" in errors[0].message

    def test_int_rule(self):
        spec = ValidationSpec(
            output_type="object",
            list_key="test_cases",
            field_rules=[FieldRule(field="step_order", type="int", min=1)],
        )
        bad = {"test_cases": [{"step_order": 0}]}
        errors = run_validations(bad, spec)
        assert any("step_order" in (e.field or "") for e in errors)

    def test_required_fields_and_item_fields(self):
        spec = ValidationSpec(
            output_type="object",
            list_key="test_cases",
            required_fields=["flow_name"],
            item_required_fields=["case_name"],
        )
        bad = {"test_cases": [{}]}
        errors = run_validations(bad, spec)
        fields = {e.field for e in errors}
        assert "flow_name" in fields
        assert "test_cases[0].case_name" in fields

    def test_unknown_custom_validator_reported(self):
        spec = ValidationSpec(output_type="object", custom_validators=["no_such_validator"])
        errors = run_validations({}, spec)
        assert any("未知校验器" in e.message for e in errors)

    def test_none_spec_returns_empty(self):
        assert run_validations({}, None) == []
