"""SkillRegistry 单例：技能注册与获取。"""

from __future__ import annotations

from src.core.logging import get_logger
from src.graph.skill.base import Skill, SkillLoader

logger = get_logger(__name__)


class SkillRegistry:
    """技能注册表（进程内单例）。"""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._loaded = False

    def register(self, skill: Skill) -> None:
        if not skill.name:
            raise ValueError("Skill 名称不能为空")
        if skill.name in self._skills:
            logger.warning(f"重复注册 skill，将覆盖: {skill.name}", skill=skill.name)
        self._skills[skill.name] = skill

    def register_dir(self, loader: SkillLoader | None = None) -> int:
        """批量注册 skills/ 目录下的所有技能，返回注册数量。"""
        loader = loader or SkillLoader()
        skills = loader.load_all()
        for skill in skills:
            self.register(skill)
        self._loaded = True
        logger.info(f"已注册 {len(skills)} 个 skill", skill_count=len(skills), skills=self.names())
        return len(skills)

    def get(self, name: str) -> Skill:
        skill = self._skills.get(name)
        if skill is None and not self._loaded:
            # 懒加载：首次访问时自动注册 skills/ 目录（避免初始化顺序耦合）
            self.register_dir()
            skill = self._skills.get(name)
        if skill is None:
            raise KeyError(f"未注册的 skill: {name}，已注册: {self.names()}")
        return skill

    def names(self) -> list[str]:
        return sorted(self._skills)


_registry = SkillRegistry()


def get_skill_registry() -> SkillRegistry:
    """获取全局 SkillRegistry 单例。"""
    return _registry


def load_skill(name: str) -> Skill:
    """便捷函数：从全局注册表获取技能。"""
    return _registry.get(name)
