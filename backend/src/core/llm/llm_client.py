"""LLM 模型工厂模块。

提供统一的工厂函数，根据配置返回对应的 LangChain BaseChatModel 实例。
支持 OpenAI、AWS Bedrock、智谱AI、通义千问。
"""

import time
from collections.abc import AsyncIterator, Iterator
from typing import Any, Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr

from src.core.config import AppConfig, get_config
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_chat_model(config: AppConfig | None = None) -> BaseChatModel:
    """根据配置创建 LangChain ChatModel 实例。

    Args:
        config: 应用配置，如果为 None 则使用全局配置

    Returns:
        BaseChatModel 实例
    """
    if config is None:
        config = get_config()

    provider = config.llm.provider.lower()

    if provider == "openai":
        logger.info("LLM提供商初始化: OpenAI", provider="openai")
        return _create_openai_model(config)
    elif provider == "bedrock":
        logger.info("LLM提供商初始化: AWS Bedrock", provider="bedrock")
        return _create_bedrock_model(config)
    elif provider == "zhipu":
        logger.info("LLM提供商初始化: 智谱AI", provider="zhipu")
        return _create_zhipu_model(config)
    elif provider == "qwen":
        logger.info("LLM提供商初始化: 通义千问", provider="qwen")
        return _create_qwen_model(config)
    elif provider == "deepseek":
        logger.info("LLM提供商初始化: Deepseek", provider="deepseek")
        return _create_deepseek_model(config)
    else:
        logger.warning(f"未知的LLM提供商: {provider}，使用OpenAI作为默认", provider=provider)
        return _create_openai_model(config)


def _create_openai_model(config: AppConfig) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    openai_config = config.llm.openai

    # 构建基础参数
    kwargs: dict = {
        "api_key": openai_config.api_key,
        "model": openai_config.model,
        "temperature": openai_config.temperature,
        "max_tokens": openai_config.max_tokens,
    }

    # 如果配置了代理地址（如 Bedrock Access Gateway），则使用代理的 base_url
    # 否则不传 base_url，ChatOpenAI 会使用默认的 OpenAI 官方地址
    if openai_config.base_url:
        kwargs["base_url"] = openai_config.base_url
        logger.info(
            "使用代理地址连接",
            base_url=openai_config.base_url,
            model=openai_config.model,
        )
    else:
        logger.info("使用OpenAI官方地址连接", model=openai_config.model)

    return ChatOpenAI(**kwargs)  # type: ignore[arg-type]


def _create_bedrock_model(config: AppConfig) -> BaseChatModel:
    import boto3  # type: ignore[import-untyped]
    from langchain_aws import ChatBedrock

    bedrock_config = config.llm.bedrock
    bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=bedrock_config.region,
        aws_access_key_id=bedrock_config.access_key,
        aws_secret_access_key=bedrock_config.secret_key,
        aws_session_token=bedrock_config.session_token or None,
    )
    return ChatBedrock(
        client=bedrock_client,
        model=bedrock_config.model_id,
        model_kwargs={"max_tokens": bedrock_config.max_tokens},
    )


def _create_zhipu_model(config: AppConfig) -> BaseChatModel:
    from langchain_community.chat_models import ChatZhipuAI

    zhipu_config = config.llm.zhipu
    return ChatZhipuAI(
        api_key=zhipu_config.api_key,
        model=zhipu_config.model,
    )


def _create_qwen_model(config: AppConfig) -> BaseChatModel:
    from langchain_community.chat_models import ChatTongyi

    qwen_config = config.llm.qwen
    return ChatTongyi(
        dashscope_api_key=SecretStr(qwen_config.api_key),  # type: ignore[call-arg]
        model=qwen_config.model,
    )


def _create_deepseek_model(config: AppConfig) -> BaseChatModel:
    deepseek_config = config.llm.deepseek
    return ChatDeepSeek(
        model=deepseek_config.model,
        api_key=SecretStr(deepseek_config.api_key),
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )


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
    """将 LangChain 消息的 content 归一化为纯文本字符串。

    部分模型（如多模态场景）会返回由字符串或字典片段组成的列表，
    此函数统一拼接为单个字符串，避免各调用点重复处理。

    Args:
        content: BaseMessage.content，可能是 str 或片段列表。

    Returns:
        归一化后的纯文本；None 或空值返回空字符串。
    """
    if isinstance(content, list):
        return "".join(part if isinstance(part, str) else str(part) for part in content)
    return content or ""


def _extract_chunk_text(chunk: BaseMessage) -> str:
    """从流式响应 chunk 中提取纯文本增量。

    Args:
        chunk: 流式迭代产出的消息块（通常为 AIMessageChunk）。

    Returns:
        该 chunk 归一化后的文本内容；无内容时返回空字符串。
    """
    return _normalize_message_content(getattr(chunk, "content", "") or "")


# ---------------------------------------------------------------------------
# 兼容层：保持 get_llm_client() 接口可用，避免一次性改动所有调用方
# ---------------------------------------------------------------------------
class LLMClient:
    """LLM 客户端兼容包装。

    内部持有 BaseChatModel 实例，提供 chat / invoke_with_tools 等便捷方法。
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
        response = self._model.invoke(langchain_messages)
        content = _normalize_message_content(response.content)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            f"LLM调用完成，耗时: {elapsed_ms}ms，响应长度: {len(content)}",
            elapsed_ms=elapsed_ms,
            response_length=len(content),
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
        return model_with_tools.invoke(messages)

    # -----------------------------------------------------------------------
    # 流式接口：文本增量（str）
    # -----------------------------------------------------------------------
    def chat_stream(self, messages: list[dict[str, str]], **kwargs) -> Iterator[str]:
        """流式发送聊天请求，逐个产出文本增量（token）。

        对应 `chat()` 的同步流式版本：不等待完整响应，而是随 LLM 生成
        实时 yield 文本片段，适用于命令行打字机效果、日志实时输出等场景。

        Args:
            messages: 字典格式消息列表，形如
                [{"role": "system/user/assistant", "content": "..."}]。
            **kwargs: 透传给底层 LangChain 模型的参数（如 stop、temperature）。

        Yields:
            str: 非空文本增量。content 为空的 chunk 会被跳过。

        Example:
            for token in client.chat_stream([{"role": "user", "content": "hi"}]):
            ... print(token, end="", flush=True)
        """
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
        """异步流式发送聊天请求，逐个产出文本增量（token）。

        对应 `chat()` 的异步流式版本，是 FastAPI SSE / WebSocket 推送等
        异步场景的首选接口。

        Args:
            messages: 字典格式消息列表，形如
                [{"role": "system/user/assistant", "content": "..."}]。
            **kwargs: 透传给底层 LangChain 模型的参数（如 stop、temperature）。

        Yields:
            str: 非空文本增量。content 为空的 chunk 会被跳过。

        Example:
            async for token in client.achat_stream(messages):
            ... await ws.send_text(token)
        """
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
        """流式产出原始消息块，保留完整 chunk 元数据。

        与 `chat_stream()` 只返回文本不同，本方法产出完整的 `AIMessageChunk`，
        便于访问 tool_call_chunks、response_metadata、usage_metadata 等高级字段。

        Args:
            messages: 字典格式消息列表（同 `chat()`）。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（通常为 AIMessageChunk）。

        Example:
            for chunk in client.stream(messages):
            ... print(chunk.content, chunk.usage_metadata)
        """
        langchain_messages = convert_to_langchain_messages(messages)
        yield from self._model.stream(langchain_messages, **kwargs)

    async def astream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[BaseMessage]:
        """异步流式产出原始消息块，保留完整 chunk 元数据。

        `stream()` 的异步版本，产出完整 `AIMessageChunk` 而非纯文本。

        Args:
            messages: 字典格式消息列表（同 `chat()`）。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（通常为 AIMessageChunk）。

        Example:
            async for chunk in client.astream(messages):
            ... print(chunk.content)
        """
        langchain_messages = convert_to_langchain_messages(messages)
        async for chunk in self._model.astream(langchain_messages, **kwargs):
            yield chunk

    def stream_messages(self, messages: list[BaseMessage], **kwargs) -> Iterator[BaseMessage]:
        """使用已转换的 LangChain 消息流式产出原始消息块。

        当调用方已持有 `BaseMessage` 列表（例如来自 LangGraph 状态），
        可直接使用本方法，跳过字典 → 消息的转换。

        Args:
            messages: 已转换的 LangChain 消息列表。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（通常为 AIMessageChunk）。

        Example:
            for chunk in client.stream_messages(lc_messages):
            ... print(chunk.content, end="")
        """
        yield from self._model.stream(messages, **kwargs)

    async def astream_messages(self, messages: list[BaseMessage], **kwargs) -> AsyncIterator[BaseMessage]:
        """使用已转换的 LangChain 消息异步流式产出原始消息块。

        `stream_messages()` 的异步版本。

        Args:
            messages: 已转换的 LangChain 消息列表。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（通常为 AIMessageChunk）。

        Example:
            async for chunk in client.astream_messages(lc_messages):
            ... print(chunk.content, end="")
        """
        async for chunk in self._model.astream(messages, **kwargs):
            yield chunk

    # -----------------------------------------------------------------------
    # 流式接口：工具绑定（返回含 tool_call_chunks 的消息块）
    # -----------------------------------------------------------------------
    def invoke_with_tools_stream(
        self,
        messages: list[BaseMessage],
        tools,
        **kwargs,
    ) -> Iterator[BaseMessage]:
        """流式发送带工具绑定的请求，产出含工具调用信息的消息块。

        对应 `invoke_with_tools()` 的流式版本。产出的 `AIMessageChunk`
        携带 `tool_call_chunks`，可用于实时观测模型的工具调用意图。

        Args:
            messages: 已转换的 LangChain 消息列表。
            tools: 待绑定的工具列表（LangChain 工具或函数 schema）。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（含 tool_call_chunks）。

        Example:
            for chunk in client.invoke_with_tools_stream(lc_messages, tools):
            ... print(chunk.tool_call_chunks)
        """
        model_with_tools = self._model.bind_tools(tools)
        yield from model_with_tools.stream(messages, **kwargs)

    async def ainvoke_with_tools_stream(
        self,
        messages: list[BaseMessage],
        tools,
        **kwargs,
    ) -> AsyncIterator[BaseMessage]:
        """异步流式发送带工具绑定的请求，产出含工具调用信息的消息块。

        `invoke_with_tools_stream()` 的异步版本。

        Args:
            messages: 已转换的 LangChain 消息列表。
            tools: 待绑定的工具列表（LangChain 工具或函数 schema）。
            **kwargs: 透传给底层 LangChain 模型的参数。

        Yields:
            BaseMessage: 每次迭代产出的原始消息块（含 tool_call_chunks）。

        Example:
            async for chunk in client.ainvoke_with_tools_stream(lc_messages, tools):
            ... print(chunk.tool_call_chunks)
        """
        model_with_tools = self._model.bind_tools(tools)
        async for chunk in model_with_tools.astream(messages, **kwargs):
            yield chunk

    # -----------------------------------------------------------------------
    # 流式接口：事件流（细粒度可观测性）
    # -----------------------------------------------------------------------
    async def astream_events(
        self,
        messages: list[dict[str, str]] | list[BaseMessage],
        version: Literal["v1", "v2"] = "v2",
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        """异步流式产出细粒度事件，用于 Agent / 链路的深度观测。

        封装 LangChain 的 `astream_events`，产出 `on_chat_model_start`、
        `on_chat_model_stream`、`on_chat_model_end` 等事件字典，是调试
        LangGraph / Agent 执行过程最常用的接口。方法会根据入参类型自动
        决定是否执行字典 → LangChain 消息的转换。

        Args:
            messages: 字典格式消息列表或已转换的 LangChain 消息列表，两者皆可。
            version: 事件 schema 版本，LangChain 当前推荐 "v2"。
            **kwargs: 透传给底层 astream_events 的参数（如 include_names）。

        Yields:
            dict[str, Any]: LangChain 事件字典，含 event、name、data 等键。

        Example:
            async for event in client.astream_events(messages):
            ... if event["event"] == "on_chat_model_stream":
            ...     print(event["data"]["chunk"].content, end="")
        """
        if messages and isinstance(messages[0], BaseMessage):
            langchain_messages = messages
        else:
            langchain_messages = convert_to_langchain_messages(messages)  # type: ignore[arg-type]
        async for event in self._model.astream_events(langchain_messages, version=version, **kwargs):
            yield cast(dict[str, Any], cast(object, event))

    def get_model(self) -> BaseChatModel:
        return self._model

    @staticmethod
    def _convert_messages_base(messages: list[dict[str, str]]) -> list[BaseMessage]:
        return convert_to_langchain_messages(messages)


_chat_model: BaseChatModel | None = None
_llm_client: LLMClient | None = None


def get_chat_model(config: AppConfig | None = None) -> BaseChatModel:
    """获取全局 ChatModel 单例。

    Args:
        config: 应用配置，如果为 None 则使用全局配置

    Returns:
        BaseChatModel 单例（create_chat_model 始终返回实例，不会为 None）
    """
    global _chat_model
    if _chat_model is None:
        _chat_model = create_chat_model(config or get_config())
    assert _chat_model is not None
    return _chat_model


def get_llm_client(config: AppConfig | None = None) -> LLMClient:
    """获取全局 LLMClient 单例（兼容旧接口）。

    Args:
        config: 应用配置，如果为 None 则使用全局配置

    Returns:
        LLMClient 单例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(get_chat_model(config))
    assert _llm_client is not None
    return _llm_client


def init_llm_client(config: AppConfig | None = None) -> LLMClient:
    """重新初始化全局 LLM 客户端。

    Args:
        config: 应用配置，如果为 None 则使用全局配置

    Returns:
        重新初始化后的 LLMClient 单例
    """
    global _chat_model, _llm_client
    _chat_model = create_chat_model(config or get_config())
    _llm_client = LLMClient(_chat_model)
    return _llm_client
