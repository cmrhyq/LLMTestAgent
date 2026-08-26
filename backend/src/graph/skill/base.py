"""Skill 数据模型与加载器。

Skill = 可复用的"方法论手册"，由 YAML 定义:
- prompt: 系统提示词（领域指令）
- user_prompt: 用户模板（str.format 占位符，对齐现有 builders）
- examples: few-shot 示例库（注入到系统提示词末尾）
- validation: 声明式校验规则（交给 validators.run_validations 执行）
- error_handling: 解析失败/校验失败/空结果的处置策略
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.core.logging import get_logger
from src.graph.skill.validators import ValidationError, run_validations

logger = get_logger(__name__)

# ---------------------------------------------------------------
# 声明式校验/处置的数据结构
# ---------------------------------------------------------------


@dataclass
class FieldRule:
    """字段级规则（枚举/类型/范围）。"""

    field: str
    type: str = "enum"  # enum | int | list | bool
    values: list | None = None
    min: int | None = None
    max: int | None = None


@dataclass
class ValidationSpec:
    """声明式校验规格。"""

    output_type: str = "object"  # object | list
    list_key: str | None = None  # object 模式下取子列表的键
    required_fields: list[str] = field(default_factory=list)  # 顶层必填
    item_required_fields: list[str] = field(default_factory=list)  # list_key 子项必填
    field_rules: list[FieldRule] = field(default_factory=list)
    custom_validators: list[str] = field(default_factory=list)


@dataclass
class ErrorHandlingSpec:
    """错误处置策略。"""

    trigger: str  # parse_failure | validation_failure | empty_result
    strategy: str  # retry_with_feedback | fallback | skip
    max_retries: int = 1
    feedback_template: str = ""
    fallback_value: Any = None


# ---------------------------------------------------------------
# Skill 数据类
# ---------------------------------------------------------------


@dataclass
class Skill:
    """技能定义：指令 + 示例 + 校验规则 + 错误处置。"""

    name: str
    description: str
    prompt: str
    user_prompt: str | None = None
    examples: list[dict] = field(default_factory=list)
    validation: ValidationSpec | None = None
    error_handling: list[ErrorHandlingSpec] = field(default_factory=list)
    source: Path | None = None

    def render_prompt(self, context: dict | None = None) -> str:
        """渲染系统提示词并追加示例库。

        Args:
            context: 可选渲染上下文（当前 prompt 无占位符，预留接口）
        """
        return inject_examples(self.prompt, self.examples)

    def build_messages(self, user_content: Any) -> list[dict[str, str]]:
        """构建 [{system}, {user}] 消息列表。

        - user_prompt 存在且 user_content 为 dict：str.format 渲染（对齐现有 builder）
        - user_prompt 存在且为 str：优先填充 {endpoints_info}，否则原样使用
        - user_prompt 不存在：JSON 序列化或原样透传
        """
        system = self.render_prompt()

        if self.user_prompt:
            if isinstance(user_content, dict):
                user = self.user_prompt.format(**user_content)
            elif isinstance(user_content, str):
                user = (
                    self.user_prompt.format(endpoints_info=user_content)
                    if "{endpoints_info}" in self.user_prompt
                    else user_content
                )
            else:
                user = str(user_content)
        elif isinstance(user_content, str):
            user = user_content
        else:
            user = json.dumps(user_content, ensure_ascii=False, default=str)

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def run_validators(self, data: Any, context: dict | None = None) -> list[ValidationError]:
        """按 validation 规格校验解析结果；未声明 validation 时返回空列表。"""
        return run_validations(data, self.validation, context)

    def handling(self, trigger: str) -> ErrorHandlingSpec | None:
        """按 trigger 查找处置策略。"""
        for spec in self.error_handling:
            if spec.trigger == trigger:
                return spec
        return None


# ---------------------------------------------------------------
# Examples 注入
# ---------------------------------------------------------------


def render_examples_block(examples: list[dict]) -> str:
    """将 few-shot 示例渲染为 markdown 段（输入/期望输出各一个 json 代码块）。"""
    if not examples:
        return ""
    lines = ["## 参考示例", ""]
    for i, ex in enumerate(examples, 1):
        lines.append(f"### 示例 {i}")
        raw_input = ex.get("input")
        if raw_input is not None:
            input_text = (
                json.dumps(raw_input, ensure_ascii=False, indent=2) if not isinstance(raw_input, str) else raw_input
            )
            lines.extend(["**输入**:", "```json", input_text, "```"])
        raw_output = ex.get("output")
        if raw_output is not None:
            output_text = (
                raw_output
                if isinstance(raw_output, str)
                else json.dumps(raw_output, ensure_ascii=False, indent=2)
            )
            lines.extend(["**期望输出**:", "```json", output_text, "```"])
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def inject_examples(system_prompt: str, examples: list[dict]) -> str:
    """将示例段追加到系统提示词末尾（无示例时原样返回）。"""
    if not examples:
        return system_prompt
    block = render_examples_block(examples)
    return f"{system_prompt.rstrip(chr(10))}\n\n{block}"


# ---------------------------------------------------------------
# SkillLoader
# ---------------------------------------------------------------

_SKILLS_DIR = Path(__file__).resolve().parent / "skills"


class SkillLoader:
    """从 skills/<name>-skill.yaml 加载技能定义。

    平铺文件命名：``<skill-name>-skill.yaml``。
    同时兼容目录格式（``<name>/skill.yaml``），便于未来某个技能
    需要 scripts/references 等配套资产时单独提升为目录。
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or _SKILLS_DIR

    def _resolve_path(self, name: str) -> Path:
        """按平铺文件优先、目录兼容的规则解析技能定义路径。"""
        flat = self.skills_dir / f"{name}-skill.yaml"
        if flat.exists():
            return flat
        dir_path = self.skills_dir / name / "skill.yaml"
        if dir_path.exists():
            return dir_path
        return flat

    def load(self, name: str) -> Skill:
        path = self._resolve_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Skill 定义不存在: {path}")
        return self._parse(path)

    def load_all(self) -> list[Skill]:
        if not self.skills_dir.exists():
            logger.warning(f"skills 目录不存在: {self.skills_dir}", skills_dir=str(self.skills_dir))
            return []
        flat_files = sorted(self.skills_dir.glob("*-skill.yaml"))
        dir_files = sorted(p / "skill.yaml" for p in self.skills_dir.iterdir() if p.is_dir())
        seen: set[Path] = set()
        paths: list[Path] = []
        for p in flat_files + dir_files:
            if p.resolve() not in seen:
                seen.add(p.resolve())
                paths.append(p)
        return [self._parse(p) for p in paths]

    # -----------------------------------------------------------
    # YAML → Skill 解析
    # -----------------------------------------------------------

    def _parse(self, path: Path) -> Skill:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        if not isinstance(raw, dict):
            raise ValueError(f"Skill 定义格式错误（顶层必须是映射）: {path}")

        name = raw.get("name", "")
        description = raw.get("description", "")
        prompt = raw.get("prompt", "")
        if not name or not description or not prompt:
            raise ValueError(f"Skill 定义缺少必填字段 name/description/prompt: {path}")

        validation_raw = raw.get("validation")
        validation = self._parse_validation(validation_raw) if validation_raw else None

        error_handling = [self._parse_error_handling(e) for e in raw.get("error_handling", [])]

        return Skill(
            name=str(name),
            description=str(description),
            prompt=str(prompt),
            user_prompt=str(raw["user_prompt"]) if raw.get("user_prompt") else None,
            examples=raw.get("examples", []) or [],
            validation=validation,
            error_handling=error_handling,
            source=path,
        )

    @staticmethod
    def _parse_validation(raw: dict) -> ValidationSpec:
        field_rules = []
        for rule in raw.get("field_rules", []) or []:
            field_rules.append(
                FieldRule(
                    field=str(rule.get("field", "")),
                    type=str(rule.get("type", "enum")),
                    values=rule.get("values"),
                    min=rule.get("min"),
                    max=rule.get("max"),
                )
            )
        return ValidationSpec(
            output_type=str(raw.get("output_type", "object")),
            list_key=raw.get("list_key"),
            required_fields=list(raw.get("required_fields", []) or []),
            item_required_fields=list(raw.get("item_required_fields", []) or []),
            field_rules=field_rules,
            custom_validators=list(raw.get("custom_validators", []) or []),
        )

    @staticmethod
    def _parse_error_handling(raw: dict) -> ErrorHandlingSpec:
        return ErrorHandlingSpec(
            trigger=str(raw.get("trigger", "")),
            strategy=str(raw.get("strategy", "skip")),
            max_retries=int(raw.get("max_retries", 1)),
            feedback_template=str(raw.get("feedback_template", "")),
            fallback_value=raw.get("fallback_value"),
        )
