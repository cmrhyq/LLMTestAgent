"""skill.yaml schema 校验测试：7 个技能资产全部可加载、字段合法、校验器引用有效。"""

import pytest

from src.graph.skill.base import SkillLoader
from src.graph.skill.validators import VALIDATORS

EXPECTED_SKILLS = {
    "single-case-generation",
    "flow-case-generation",
    "security-audit",
    "assertion-authoring",
    "complexity-assessment",
    "report-generation",
    "openapi-onboarding",
}

VALID_TOP_LEVEL_KEYS = {"name", "description", "prompt", "user_prompt", "examples", "validation", "error_handling"}
VALID_OUTPUT_TYPES = {"object", "list"}
VALID_TRIGGERS = {"parse_failure", "validation_failure", "empty_result"}
VALID_STRATEGIES = {"retry_with_feedback", "fallback", "skip"}


def _load_skills() -> list:
    return SkillLoader().load_all()


@pytest.mark.unit
class TestSkillSchema:
    """遍历 7 个 skill.yaml 做结构校验。"""

    def test_all_expected_skills_present(self):
        names = {s.name for s in _load_skills()}
        assert names == EXPECTED_SKILLS, f"技能集合不匹配，缺失: {EXPECTED_SKILLS - names}，多余: {names - EXPECTED_SKILLS}"

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
    def test_skill_loads_and_has_required_fields(self, skill_name):
        skill = SkillLoader().load(skill_name)
        assert skill.name == skill_name
        assert skill.description
        assert skill.prompt
        assert skill.source is not None and skill.source.name == f"{skill_name}-skill.yaml"

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
    def test_top_level_keys_valid(self, skill_name):
        from pathlib import Path

        import yaml

        path = Path("src/graph/skill/skills") / f"{skill_name}-skill.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(raw) <= VALID_TOP_LEVEL_KEYS, f"非法顶层键: {set(raw) - VALID_TOP_LEVEL_KEYS}"

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
    def test_custom_validators_exist(self, skill_name):
        skill = SkillLoader().load(skill_name)
        if skill.validation:
            for name in skill.validation.custom_validators:
                assert name in VALIDATORS, f"{skill_name} 引用未知校验器: {name}"

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
    def test_validation_spec_structure(self, skill_name):
        skill = SkillLoader().load(skill_name)
        if skill.validation is None:
            return
        v = skill.validation
        assert v.output_type in VALID_OUTPUT_TYPES
        if v.output_type == "object" and v.list_key:
            assert isinstance(v.list_key, str)
        for rule in v.field_rules:
            assert rule.field
            assert rule.type in {"enum", "int", "list", "bool"}

    @pytest.mark.parametrize("skill_name", sorted(EXPECTED_SKILLS))
    def test_error_handling_structure(self, skill_name):
        skill = SkillLoader().load(skill_name)
        for spec in skill.error_handling:
            assert spec.trigger in VALID_TRIGGERS, f"{skill_name} 非法 trigger: {spec.trigger}"
            assert spec.strategy in VALID_STRATEGIES, f"{skill_name} 非法 strategy: {spec.strategy}"
            assert spec.max_retries >= 0

    def test_skill_with_examples_injectable(self):
        skill = SkillLoader().load("single-case-generation")
        assert skill.examples, "single-case-generation 应有示例库"
        for ex in skill.examples:
            assert "input" in ex and "output" in ex
