"""llm_utils 模块单元测试。

覆盖：robust_json_loads、safe_json_loads、get_model_name、
      parse_llm_json_response、ensure_db。
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_logger():
    """Mock logger 避免测试输出噪声。"""
    import src.utils.llm_utils as module

    with patch.object(module, "logger", MagicMock()):
        yield


@pytest.mark.unit
class TestRobustJsonLoads:
    """robust_json_loads 测试。"""

    def test_valid_json_object(self):
        from src.utils.llm_utils import robust_json_loads

        result = robust_json_loads('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_valid_json_array(self):
        from src.utils.llm_utils import robust_json_loads

        result = robust_json_loads("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_repairable_json(self):
        from src.utils.llm_utils import robust_json_loads

        result = robust_json_loads("{key: 'value'}")
        assert isinstance(result, dict)
        assert result.get("key") == "value"

    def test_completely_invalid_raises(self):
        from src.utils.llm_utils import robust_json_loads

        with pytest.raises((json.JSONDecodeError, TypeError)):
            robust_json_loads(None)

    def test_empty_string_returns_repaired(self):
        from src.utils.llm_utils import robust_json_loads

        result = robust_json_loads("")
        assert result == "" or result is None or result == {}

    def test_none_input_raises(self):
        from src.utils.llm_utils import robust_json_loads

        with pytest.raises((json.JSONDecodeError, TypeError)):
            robust_json_loads(None)

    def test_trailing_comma_repaired(self):
        from src.utils.llm_utils import robust_json_loads

        result = robust_json_loads('{"a": 1, "b": 2,}')
        assert result == {"a": 1, "b": 2}


@pytest.mark.unit
class TestSafeJsonLoads:
    """safe_json_loads 测试。"""

    def test_none_returns_default(self):
        from src.utils.llm_utils import safe_json_loads

        assert safe_json_loads(None, []) == []
        assert safe_json_loads(None, {}) == {}

    def test_empty_string_returns_default(self):
        from src.utils.llm_utils import safe_json_loads

        assert safe_json_loads("", "fallback") == "fallback"

    def test_valid_json_parsed(self):
        from src.utils.llm_utils import safe_json_loads

        result = safe_json_loads('{"x": 1}', {})
        assert result == {"x": 1}

    def test_invalid_json_returns_repaired_or_default(self):
        from src.utils.llm_utils import safe_json_loads

        result = safe_json_loads("not json !!!", {"default": True})
        assert result == "" or result == {"default": True}

    def test_repairable_json_parsed(self):
        from src.utils.llm_utils import safe_json_loads

        result = safe_json_loads("{key: 'val'}", None)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestGetModelName:
    """get_model_name 测试。"""

    def _make_config(self, provider: str, **kwargs):
        config = MagicMock()
        config.llm.provider = provider
        config.llm.openai.model = kwargs.get("openai_model", "gpt-4")
        config.llm.bedrock.model_id = kwargs.get("bedrock_model", "anthropic.claude-v2")
        config.llm.zhipu.model = kwargs.get("zhipu_model", "glm-4")
        config.llm.qwen.model = kwargs.get("qwen_model", "qwen-turbo")
        return config

    def test_openai_provider(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("openai", openai_model="gpt-4o")
        assert get_model_name(config) == "gpt-4o"

    def test_bedrock_provider(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("bedrock", bedrock_model="anthropic.claude-3")
        assert get_model_name(config) == "anthropic.claude-3"

    def test_zhipu_provider(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("zhipu", zhipu_model="glm-4-plus")
        assert get_model_name(config) == "glm-4-plus"

    def test_qwen_provider(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("qwen", qwen_model="qwen-max")
        assert get_model_name(config) == "qwen-max"

    def test_unknown_provider_returns_provider_name(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("custom_llm")
        assert get_model_name(config) == "custom_llm"

    def test_case_insensitive(self):
        from src.utils.llm_utils import get_model_name

        config = self._make_config("OpenAI", openai_model="gpt-4")
        assert get_model_name(config) == "gpt-4"


@pytest.mark.unit
class TestParseLlmJsonResponse:
    """parse_llm_json_response 测试。"""

    def test_markdown_code_block_json(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '```json\n{"test_cases": [{"id": 1}, {"id": 2}]}\n```'
        result = parse_llm_json_response(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_markdown_code_block_no_lang(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '```\n{"test_cases": [{"id": 1}]}\n```'
        result = parse_llm_json_response(response)
        assert result == [{"id": 1}]

    def test_plain_json_dict(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '{"test_cases": [{"name": "a"}, {"name": "b"}]}'
        result = parse_llm_json_response(response)
        assert result == [{"name": "a"}, {"name": "b"}]

    def test_plain_json_with_surrounding_text(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = 'Here is the result: {"test_cases": [{"id": 1}]} Hope this helps!'
        result = parse_llm_json_response(response)
        assert result == [{"id": 1}]

    def test_custom_list_key(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '{"cases": [{"x": 1}]}'
        result = parse_llm_json_response(response, list_key="cases")
        assert result == [{"x": 1}]

    def test_result_is_list_directly(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '```json\n[{"id": 1}, {"id": 2}]\n```'
        result = parse_llm_json_response(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_sort_key(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '{"test_cases": [{"priority": 3}, {"priority": 1}, {"priority": 2}]}'
        result = parse_llm_json_response(response, sort_key="priority")
        assert result == [{"priority": 1}, {"priority": 2}, {"priority": 3}]

    def test_no_json_content_returns_empty(self):
        from src.utils.llm_utils import parse_llm_json_response

        result = parse_llm_json_response("No JSON here at all")
        assert result == []

    def test_dict_with_non_list_value_returns_empty(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '{"test_cases": "not a list"}'
        result = parse_llm_json_response(response)
        assert result == []

    def test_non_dict_non_list_returns_empty(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = "```json\n42\n```"
        result = parse_llm_json_response(response)
        assert result == []

    def test_missing_list_key_returns_empty(self):
        from src.utils.llm_utils import parse_llm_json_response

        response = '{"other_key": [{"id": 1}]}'
        result = parse_llm_json_response(response)
        assert result == []


@pytest.mark.unit
class TestEnsureDb:
    """ensure_db 测试。"""

    @patch("src.utils.llm_utils.get_config")
    @patch("src.utils.llm_utils.get_db_manager")
    def test_calls_initialize_when_not_initialized(self, mock_get_db, mock_get_cfg):
        from src.utils.llm_utils import ensure_db

        manager = MagicMock()
        manager._initialized = False
        mock_get_db.return_value = manager

        config = MagicMock()
        config.database.url = "sqlite:///test.db"
        config.database.echo = False
        config.database.pool_size = 5
        config.database.max_overflow = 10
        config.database.pool_timeout = 30
        config.database.pool_recycle = 3600
        mock_get_cfg.return_value = config

        ensure_db()

        manager.initialize.assert_called_once_with(
            db_url="sqlite:///test.db",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
        )

    @patch("src.utils.llm_utils.get_config")
    @patch("src.utils.llm_utils.get_db_manager")
    def test_skips_when_already_initialized(self, mock_get_db, mock_get_cfg):
        from src.utils.llm_utils import ensure_db

        manager = MagicMock()
        manager._initialized = True
        mock_get_db.return_value = manager

        ensure_db()

        manager.initialize.assert_not_called()
        mock_get_cfg.assert_not_called()
