"""Pytest 配置验证 — 确保基本配置和 fixture 正常工作。"""

import pytest


class TestPytestSetup:
    """验证 pytest 环境配置正确。"""

    def test_space_root_exists(self, project_root):
        assert project_root.exists()
        assert (project_root / "pyproject.toml").exists()

    def test_input_dir_exists(self, input_dir):
        assert input_dir.exists()

    def test_env_is_test(self, monkeypatch):
        import os

        assert os.environ.get("LLMTESTAGENT_ENV") == "test"


@pytest.mark.unit
class TestImports:
    """验证核心模块可正常导入。"""

    def test_import_config(self):
        from src.core.config import AppConfig

        assert AppConfig is not None

    def test_import_workflow(self):
        from src.workflow import TestWorkflow, build_graph

        assert TestWorkflow is not None
        assert build_graph is not None

    def test_import_openapi_parser(self):
        from src.utils.parser import OpenAPIParser

        assert OpenAPIParser is not None

    def test_import_prompt_loader(self):
        from src.prompts.loader import PromptLoader

        assert PromptLoader is not None
