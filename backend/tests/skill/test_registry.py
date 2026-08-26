"""SkillRegistry 测试。"""

import pytest

from src.graph.skill.base import Skill, SkillLoader
from src.graph.skill.registry import SkillRegistry


def _make_skill(name: str) -> Skill:
    return Skill(name=name, description=f"{name} desc", prompt="prompt")


@pytest.mark.unit
class TestSkillRegistry:
    """注册表行为。"""

    def test_register_and_get(self):
        registry = SkillRegistry()
        registry.register(_make_skill("a"))
        assert registry.get("a").name == "a"
        assert registry.names() == ["a"]

    def test_register_dir_loads_disk_skills(self):
        registry = SkillRegistry()
        count = registry.register_dir()
        assert count == 7
        assert "single-case-generation" in registry.names()

    def test_get_unknown_raises_with_candidates(self):
        registry = SkillRegistry()
        registry.register(_make_skill("a"))
        with pytest.raises(KeyError) as exc:
            registry.get("b")
        assert "a" in str(exc.value)

    def test_duplicate_register_overwrites(self):
        registry = SkillRegistry()
        registry.register(_make_skill("a"))
        registry.register(_make_skill("a"))
        assert len(registry.names()) == 1

    def test_lazy_register_dir_on_first_get(self, tmp_path, monkeypatch):
        """单例首次 get 时自动注册磁盘技能。"""
        from src.graph.skill import registry as registry_module

        fresh = SkillRegistry()
        monkeypatch.setattr(registry_module, "_registry", fresh)
        skill = registry_module.get_skill_registry().get("single-case-generation")
        assert skill.name == "single-case-generation"
        assert fresh._loaded is True

    def test_custom_loader_directory(self, tmp_path):
        (tmp_path / "custom-skill.yaml").write_text(
            "name: custom\ndescription: d\nprompt: p\n", encoding="utf-8"
        )
        registry = SkillRegistry()
        registry.register_dir(SkillLoader(skills_dir=tmp_path))
        assert registry.get("custom").name == "custom"
