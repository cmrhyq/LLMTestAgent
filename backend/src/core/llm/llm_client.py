"""LLM 模型工厂模块。

基于 LiteLLM Router + langchain-litellm 提供统一的 BaseChatModel 实例。
通过 config.yaml 的 ``model_list`` 配置多模型路由（fallback / load balancing），
通过 ``llm.default_model`` 指定默认模型名。

调用方统一使用 ``get_llm_client()`` 或 ``get_chat_model()``，无需关心底层 provider。
"""

import time
from collections.abc import AsyncIterator, Iterator
from typing import Any, Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router

from src.core.config import get_config
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_chat_model() -> BaseChatModel:
    """根据配置创建 LangChain ChatModel 实例（基于 LiteLLM Router）。

    从 ``config.model_list`` 构建 litellm.Router，再包装为
    ``ChatLiteLLMRouter``（继承 BaseChatModel）。

    Returns:
        BaseChatModel 实例（ChatLiteLLMRouter）

    Raises:
        ValueError: config.model_list 为空时
    """
    config = get_config()
    if not config.model_list:
        raise ValueError("config.yaml 中缺少 model_list 配置，无法构建 LLM Router")

    default_model = config.llm.default_model
    logger.info(
        "LLM Router 初始化",
        default_model=default_model,
        model_count=len(config.model_list),
    )

    router = Router(model_list=config.model_list)
    return ChatLiteLLMRouter(router=router, model=default_model)


def convert_to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    """将字典格式消息列表转换为 LangChain BaseMessage 列表。

    Args:
        messages: [{"role": "system/user/assistant", "content": "..."}]

    Returns:
        LangChain 消息列表
    """
    result: list[BaseMessage] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
        else:
            result.append(HumanMessage(content=content))
    return result


def _normalize_message_content(content: str | list) -> str:
    """将 LangChain 消息的 content 归一化为纯文本字符串。"""
    if isinstance(content, list):
        return "".join(part if isinstance(part, str) else str(part) for part in content)
    return content or ""


def _extract_chunk_text(chunk: BaseMessage) -> str:
    """从流式响应 chunk 中提取纯文本增量。"""
    return _normalize_message_content(getattr(chunk, "content", "") or "")


class LLMClient:
    """LLM 客户端兼容包装。

    内部持有 BaseChatModel（ChatLiteLLMRouter）实例，
    提供 chat / invoke_with_tools / stream 等便捷方法。
    """

    def __init__(self, model: BaseChatModel):
        self._model = model

    @property
    def model(self) -> BaseChatModel:
        return self._model

    def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """发送聊天请求，返回纯文本响应。"""
        logger.debug(f"LLM调用开始，消息数: {len(messages)}", message_count=len(messages))
        start_time = time.perf_counter()
        langchain_messages = convert_to_langchain_messages(messages)
        response = self._model.invoke(langchain_messages, **kwargs)

        content = _normalize_message_content(response.content)
        usage_metadata = response.usage_metadata
        response_metadata = response.response_metadata

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            f"LLM调用完成，耗时: {elapsed_ms}ms，响应长度: {len(content)}",
            elapsed_ms=elapsed_ms,
            response_length=len(content),
            usage_metadata=usage_metadata,
            response_metadata=response_metadata
        )
        return content

    def invoke_with_tools(
        self,
        messages: list[BaseMessage],
        tools,
        **kwargs,
    ) -> BaseMessage:
        """使用已转换的消息发送带工具绑定的请求。"""
        model_with_tools = self._model.bind_tools(tools)
        response = model_with_tools.invoke(messages, **kwargs)

        usage_metadata = response.usage_metadata
        response_metadata = response.response_metadata

        logger.debug(
            f"Invoke With Tools 调用完成，使用工具：{tools}",
            usage_metadata=usage_metadata,
            response_metadata=response_metadata
        )
        return response

    # -----------------------------------------------------------------------
    # 流式接口：文本增量（str）
    # -----------------------------------------------------------------------
    def chat_stream(self, messages: list[dict[str, str]], **kwargs) -> Iterator[str]:
        """流式发送聊天请求，逐个产出文本增量（token）。"""
        logger.debug(f"LLM流式调用开始，消息数: {len(messages)}", message_count=len(messages))
        start_time = time.perf_counter()
        langchain_messages = convert_to_langchain_messages(messages)
        total_length = 0
        for chunk in self._model.stream(langchain_messages, **kwargs):
            text = _extract_chunk_text(chunk)
            if text:
                total_length += len(text)
                yield text
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            f"LLM流式调用完成，耗时: {elapsed_ms}ms，累计响应长度: {total_length}",
            elapsed_ms=elapsed_ms,
            response_length=total_length,
        )

    async def achat_stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """异步流式发送聊天请求，逐个产出文本增量（token）。"""
        logger.debug(f"LLM异步流式调用开始，消息数: {len(messages)}", message_count=len(messages))
        start_time = time.perf_counter()
        langchain_messages = convert_to_langchain_messages(messages)
        total_length = 0
        async for chunk in self._model.astream(langchain_messages, **kwargs):
            text = _extract_chunk_text(chunk)
            if text:
                total_length += len(text)
                yield text
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            f"LLM异步流式调用完成，耗时: {elapsed_ms}ms，累计响应长度: {total_length}",
            elapsed_ms=elapsed_ms,
            response_length=total_length,
        )

    # -----------------------------------------------------------------------
    # 流式接口：原始消息块（BaseMessage / AIMessageChunk）
    # -----------------------------------------------------------------------
    def stream(self, messages: list[dict[str, str]], **kwargs) -> Iterator[BaseMessage]:
        """流式产出原始消息块，保留完整 chunk 元数据（tool_call_chunks 等）。"""
        langchain_messages = convert_to_langchain_messages(messages)
        yield from self._model.stream(langchain_messages, **kwargs)

    async def astream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[BaseMessage]:
        """异步流式产出原始消息块。"""
        langchain_messages = convert_to_langchain_messages(messages)
        async for chunk in self._model.astream(langchain_messages, **kwargs):
            yield chunk

    def stream_messages(self, messages: list[BaseMessage], **kwargs) -> Iterator[BaseMessage]:
        """使用已转换的 LangChain 消息流式产出原始消息块。"""
        yield from self._model.stream(messages, **kwargs)

    async def astream_messages(self, messages: list[BaseMessage], **kwargs) -> AsyncIterator[BaseMessage]:
        """使用已转换的 LangChain 消息异步流式产出原始消息块。"""
        async for chunk in self._model.astream(messages, **kwargs):
            yield chunk

    # -----------------------------------------------------------------------
    # 流式接口：工具绑定
    # -----------------------------------------------------------------------
    def invoke_with_tools_stream(
        self,
        messages: list[BaseMessage],
        tools,
        **kwargs,
    ) -> Iterator[BaseMessage]:
        """流式发送带工具绑定的请求，产出含 tool_call_chunks 的消息块。"""
        model_with_tools = self._model.bind_tools(tools)
        yield from model_with_tools.stream(messages, **kwargs)

    async def ainvoke_with_tools_stream(
        self,
        messages: list[BaseMessage],
        tools,
        **kwargs,
    ) -> AsyncIterator[BaseMessage]:
        """异步流式发送带工具绑定的请求。"""
        model_with_tools = self._model.bind_tools(tools)
        async for chunk in model_with_tools.astream(messages, **kwargs):
            yield chunk

    # -----------------------------------------------------------------------
    # 事件流（细粒度可观测性）
    # -----------------------------------------------------------------------
    async def astream_events(
        self,
        messages: list[dict[str, str]] | list[BaseMessage],
        version: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        """异步流式产出细粒度事件（on_chat_model_stream 等）。"""
        if messages and isinstance(messages[0], BaseMessage):
            langchain_messages = messages
        else:
            langchain_messages = convert_to_langchain_messages(messages)  # type: ignore[arg-type]
        async for event in self._model.astream_events(langchain_messages, version=version, **kwargs):
            yield cast(dict[str, Any], cast(object, event))

    def get_model(self) -> BaseChatModel:
        return self._model


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_chat_model: BaseChatModel | None = None
_llm_client: LLMClient | None = None


def get_chat_model() -> BaseChatModel:
    """获取全局 ChatModel 单例。"""
    global _chat_model
    if _chat_model is None:
        _chat_model = create_chat_model()
    assert _chat_model is not None
    return _chat_model


def get_llm_client() -> LLMClient:
    """获取全局 LLMClient 单例。"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(get_chat_model())
    assert _llm_client is not None
    return _llm_client


def init_llm_client() -> LLMClient:
    """重新初始化全局 LLM 客户端。"""
    global _chat_model, _llm_client
    _chat_model = create_chat_model()
    _llm_client = LLMClient(_chat_model)
    return _llm_client
