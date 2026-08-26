"""Skill 数据类与加载器测试。"""

import pytest

from src.graph.skill.base import (
    ErrorHandlingSpec,
    Skill,
    SkillLoader,
    ValidationSpec,
    inject_examples,
    render_examples_block,
)


@pytest.mark.unit
class TestExamplesInjection:
    """examples 注入与渲染。"""

    def test_render_examples_block(self):
        block = render_examples_block(
            [{"input": {"url": "/x"}, "output": '{"test_cases": []}'}]
        )
        assert "## 参考示例" in block
        assert "### 示例 1" in block
        assert "**输入**" in block
        assert "**期望输出**" in block
        assert '```json' in block

    def test_inject_examples_appends(self):
        result = inject_examples("系统提示词", [{"input": {}, "output": "{}"}])
        assert result.startswith("系统提示词")
        assert "## 参考示例" in result

    def test_inject_examples_noop_without_examples(self):
        prompt = "系统提示词"
        assert inject_examples(prompt, []) == prompt


@pytest.mark.unit
class TestSkillBuildMessages:
    """build_messages 的三种 user 渲染路径。"""

    def _make_skill(self, user_prompt=None):
        return Skill(
            name="t",
            description="t",
            prompt="system",
            user_prompt=user_prompt,
            examples=[],
            validation=ValidationSpec(output_type="object"),
            error_handling=[],
        )

    def test_dict_user_content_formats(self):
        skill = self._make_skill(user_prompt="接口: {name}, 地址: {url}")
        messages = skill.build_messages({"name": "登录", "url": "/login"})
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "接口: 登录, 地址: /login"

    def test_str_user_content_with_endpoints_info(self):
        skill = self._make_skill(user_prompt="接口列表: {endpoints_info}")
        messages = skill.build_messages('[{"id": 1}]')
        assert messages[1]["content"] == "接口列表: [{\"id\": 1}]"

    def test_str_user_content_without_placeholder_passthrough(self):
        skill = self._make_skill(user_prompt="固定问题")
        messages = skill.build_messages("自定义输入")
        assert messages[1]["content"] == "自定义输入"

    def test_no_user_prompt_serializes_dict(self):
        skill = self._make_skill()
        messages = skill.build_messages({"a": 1})
        assert '"a"' in messages[1]["content"]

    def test_error_handling_lookup(self):
        skill = Skill(
            name="t", description="t", prompt="p",
            error_handling=[ErrorHandlingSpec(trigger="parse_failure", strategy="retry_with_feedback", max_retries=1)],
        )
        spec = skill.handling("parse_failure")
        assert spec is not None and spec.strategy == "retry_with_feedback"
        assert skill.handling("validation_failure") is None


@pytest.mark.unit
class TestSkillLoader:
    """加载器行为。"""

    def test_load_unknown_skill_raises(self):
        with pytest.raises(FileNotFoundError):
            SkillLoader().load("not-exist")

    def test_load_all_returns_seven(self):
        skills = SkillLoader().load_all()
        assert len(skills) == 7

    def test_missing_required_field_raises(self, tmp_path):
        (tmp_path / "bad-skill.yaml").write_text("name: x\n", encoding="utf-8")
        loader = SkillLoader(skills_dir=tmp_path)
        with pytest.raises(ValueError, match="description"):
            loader.load("bad")

    def test_directory_layout_still_compatible(self, tmp_path):
        """目录格式(<name>/skill.yaml)仍被兼容,便于未来资产扩展。"""
        (tmp_path / "flat-skill.yaml").write_text(
            "name: flat\ndescription: d\nprompt: p\n", encoding="utf-8"
        )
        skill_dir = tmp_path / "legacy"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(
            "name: legacy\ndescription: d\nprompt: p\n", encoding="utf-8"
        )
        loader = SkillLoader(skills_dir=tmp_path)
        assert loader.load("flat").name == "flat"
        assert loader.load("legacy").name == "legacy"
        assert len(loader.load_all()) == 2  # 平铺 + 目录各一个
