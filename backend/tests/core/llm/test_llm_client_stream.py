"""LLMClient 流式方法单元测试。

覆盖：chat_stream、achat_stream、stream / astream、stream_messages /
      astream_messages、invoke_with_tools_stream / ainvoke_with_tools_stream、
      astream_events，以及公共 helper _normalize_message_content /
      _extract_chunk_text。

所有测试均使用 MagicMock 模拟 BaseChatModel，不发起真实 LLM 请求。
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage


@pytest.fixture(autouse=True)
def _mock_logger():
    """Mock logger 避免测试输出噪声。"""
    import src.core.llm.llm_client as module

    with patch.object(module, "logger", MagicMock()):
        yield


def _make_client(model):
    """使用给定的 mock 模型构造 LLMClient。"""
    from src.core.llm.llm_client import LLMClient

    return LLMClient(model)


def _async_gen(items):
    """将同步序列包装为异步生成器，用于模拟 astream。"""

    async def _gen(*args, **kwargs):
        for item in items:
            yield item

    return _gen


@pytest.mark.unit
class TestNormalizeMessageContent:
    """_normalize_message_content 测试。"""

    def test_plain_string(self):
        from src.core.llm.llm_client import _normalize_message_content

        assert _normalize_message_content("hello") == "hello"

    def test_none_returns_empty(self):
        from src.core.llm.llm_client import _normalize_message_content

        assert _normalize_message_content(None) == ""  # type: ignore[arg-type]

    def test_list_of_strings(self):
        from src.core.llm.llm_client import _normalize_message_content

        assert _normalize_message_content(["a", "b", "c"]) == "abc"

    def test_list_with_non_string_parts(self):
        from src.core.llm.llm_client import _normalize_message_content

        result = _normalize_message_content(["a", {"type": "text"}])
        assert result.startswith("a")
        assert "type" in result


@pytest.mark.unit
class TestExtractChunkText:
    """_extract_chunk_text 测试。"""

    def test_chunk_with_content(self):
        from src.core.llm.llm_client import _extract_chunk_text

        assert _extract_chunk_text(AIMessageChunk(content="hi")) == "hi"

    def test_chunk_without_content(self):
        from src.core.llm.llm_client import _extract_chunk_text

        assert _extract_chunk_text(AIMessageChunk(content="")) == ""

    def test_object_without_content_attr(self):
        from src.core.llm.llm_client import _extract_chunk_text

        assert _extract_chunk_text(object()) == ""  # type: ignore[arg-type]


@pytest.mark.unit
class TestChatStream:
    """chat_stream 测试。"""

    def test_concatenation_matches_full_text(self):
        model = MagicMock()
        model.stream.return_value = [
            AIMessageChunk(content="Hel"),
            AIMessageChunk(content="lo"),
        ]
        client = _make_client(model)

        tokens = list(client.chat_stream([{"role": "user", "content": "hi"}]))

        assert tokens == ["Hel", "lo"]
        assert "".join(tokens) == "Hello"

    def test_empty_chunks_skipped(self):
        model = MagicMock()
        model.stream.return_value = [
            AIMessageChunk(content="A"),
            AIMessageChunk(content=""),
            AIMessageChunk(content="B"),
        ]
        client = _make_client(model)

        tokens = list(client.chat_stream([{"role": "user", "content": "hi"}]))

        assert tokens == ["A", "B"]

    def test_list_content_normalized(self):
        model = MagicMock()
        model.stream.return_value = [AIMessageChunk(content=["x", "y"])]
        client = _make_client(model)

        tokens = list(client.chat_stream([{"role": "user", "content": "hi"}]))

        assert tokens == ["xy"]

    def test_kwargs_passed_through(self):
        model = MagicMock()
        model.stream.return_value = [AIMessageChunk(content="ok")]
        client = _make_client(model)

        list(client.chat_stream([{"role": "user", "content": "hi"}], stop=["\n"]))

        _, kwargs = model.stream.call_args
        assert kwargs.get("stop") == ["\n"]


@pytest.mark.unit
class TestAchatStream:
    """achat_stream 测试。"""

    async def test_async_concatenation(self):
        model = MagicMock()
        model.astream = _async_gen([AIMessageChunk(content="Wor"), AIMessageChunk(content="ld")])
        client = _make_client(model)

        tokens = [tok async for tok in client.achat_stream([{"role": "user", "content": "hi"}])]

        assert tokens == ["Wor", "ld"]

    async def test_async_empty_skipped(self):
        model = MagicMock()
        model.astream = _async_gen([AIMessageChunk(content=""), AIMessageChunk(content="Z")])
        client = _make_client(model)

        tokens = [tok async for tok in client.achat_stream([{"role": "user", "content": "hi"}])]

        assert tokens == ["Z"]


@pytest.mark.unit
class TestRawStream:
    """stream / astream / stream_messages / astream_messages 测试。"""

    def test_stream_yields_raw_chunks(self):
        chunks = [AIMessageChunk(content="a"), AIMessageChunk(content="b")]
        model = MagicMock()
        model.stream.return_value = chunks
        client = _make_client(model)

        result = list(client.stream([{"role": "user", "content": "hi"}]))

        assert result == chunks
        assert all(isinstance(c, BaseMessage) for c in result)

    async def test_astream_yields_raw_chunks(self):
        chunks = [AIMessageChunk(content="a"), AIMessageChunk(content="b")]
        model = MagicMock()
        model.astream = _async_gen(chunks)
        client = _make_client(model)

        result = [c async for c in client.astream([{"role": "user", "content": "hi"}])]

        assert result == chunks

    def test_stream_messages_bypasses_conversion(self):
        chunks = [AIMessageChunk(content="a")]
        model = MagicMock()
        model.stream.return_value = chunks
        client = _make_client(model)

        lc_messages = [HumanMessage(content="hi")]
        result = list(client.stream_messages(lc_messages))

        assert result == chunks
        args, _ = model.stream.call_args
        assert args[0] is lc_messages

    async def test_astream_messages_bypasses_conversion(self):
        chunks = [AIMessageChunk(content="a")]
        model = MagicMock()
        model.astream = _async_gen(chunks)
        client = _make_client(model)

        lc_messages = [HumanMessage(content="hi")]
        result = [c async for c in client.astream_messages(lc_messages)]

        assert result == chunks


@pytest.mark.unit
class TestToolsStream:
    """invoke_with_tools_stream / ainvoke_with_tools_stream 测试。"""

    def test_binds_tools_and_streams(self):
        bound = MagicMock()
        bound.stream.return_value = [AIMessageChunk(content="t")]
        model = MagicMock()
        model.bind_tools.return_value = bound
        client = _make_client(model)

        tools = [{"name": "dummy"}]
        lc_messages = [HumanMessage(content="hi")]
        result = list(client.invoke_with_tools_stream(lc_messages, tools))

        model.bind_tools.assert_called_once_with(tools)
        bound.stream.assert_called_once()
        assert result == [AIMessageChunk(content="t")]

    async def test_async_binds_tools_and_streams(self):
        bound = MagicMock()
        bound.astream = _async_gen([AIMessageChunk(content="t")])
        model = MagicMock()
        model.bind_tools.return_value = bound
        client = _make_client(model)

        tools = [{"name": "dummy"}]
        lc_messages = [HumanMessage(content="hi")]
        result = [c async for c in client.ainvoke_with_tools_stream(lc_messages, tools)]

        model.bind_tools.assert_called_once_with(tools)
        assert result == [AIMessageChunk(content="t")]


@pytest.mark.unit
class TestAstreamEvents:
    """astream_events 测试。"""

    async def test_converts_dict_messages(self):
        events = [{"event": "on_chat_model_stream"}]
        model = MagicMock()
        model.astream_events = _async_gen(events)
        client = _make_client(model)

        with patch(
            "src.core.llm.llm_client.convert_to_langchain_messages",
            return_value=[HumanMessage(content="hi")],
        ) as mock_convert:
            result = [e async for e in client.astream_events([{"role": "user", "content": "hi"}])]

        mock_convert.assert_called_once()
        assert result == events

    async def test_skips_conversion_for_base_messages(self):
        events = [{"event": "on_chat_model_end"}]
        model = MagicMock()
        model.astream_events = _async_gen(events)
        client = _make_client(model)

        with patch("src.core.llm.llm_client.convert_to_langchain_messages") as mock_convert:
            lc_messages = [HumanMessage(content="hi")]
            result = [e async for e in client.astream_events(lc_messages)]

        mock_convert.assert_not_called()
        assert result == events

    async def test_version_and_kwargs_passed(self):
        model = MagicMock()
        model.astream_events = MagicMock(side_effect=_async_gen([]))
        client = _make_client(model)

        lc_messages = [HumanMessage(content="hi")]
        [e async for e in client.astream_events(lc_messages, version="v1", include_names=["x"])]

        _, kwargs = model.astream_events.call_args
        assert kwargs.get("version") == "v1"
        assert kwargs.get("include_names") == ["x"]

    async def test_empty_messages_uses_conversion(self):
        model = MagicMock()
        model.astream_events = _async_gen([])
        client = _make_client(model)

        with patch(
            "src.core.llm.llm_client.convert_to_langchain_messages",
            return_value=[],
        ) as mock_convert:
            [e async for e in client.astream_events([])]

        mock_convert.assert_called_once()
