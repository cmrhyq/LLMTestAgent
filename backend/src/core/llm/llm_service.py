"""基于 LiteLLM Router 的统一 LLM 服务。

使用 ``langchain-litellm`` 的 ``ChatLiteLLMRouter`` 包装 ``litellm.Router``，
提供统一的 LangChain BaseChatModel 接口：invoke / stream / bind_tools / astream_events。

所有方法直接接收 ``list[BaseMessage]``。

配置来源：``config.model_list``（模型路由列表）+ ``config.llm.default_model``（默认模型名）。

用法::

    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from src.core.llm.llm_service import get_llm_service

    service = get_llm_service()

    # 基础调用（system + user 消息）
    response = service.invoke([
        SystemMessage(content="你是一个 API 测试助手"),
        HumanMessage(content="帮我测试登录接口"),
    ])
    print(response.content)           # 文本回答
    print(response.usage_metadata)    # {"input_tokens": N, "output_tokens": N, "total_tokens": N}

    # 多轮对话（含历史 assistant 消息）
    response = service.invoke([
        SystemMessage(content="你是一个 API 测试助手"),
        HumanMessage(content="帮我测试登录接口"),
        AIMessage(content="好的，我来帮你设计测试用例..."),
        HumanMessage(content="再加一个异常场景"),
    ])

    # 流式输出
    for chunk in service.stream([HumanMessage(content="解释什么是接口测试")]):
        print(chunk.content, end="")  # 逐 token 输出

    # 工具调用
    from langchain_core.tools import tool

    @tool
    def get_endpoints(space_id: int) -> str:
        \"\"\"查询空间下的接口列表。\"\"\"
        return "..."

    response = service.invoke_with_tools(
        [HumanMessage(content="查询空间 1 的接口")],
        tools=[get_endpoints],
    )
    print(response.tool_calls)        # [{"name": "get_endpoints", "args": {"space_id": 1}, ...}]
"""

from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router

from src.core.config import AppConfig, get_config
from src.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """基于 LiteLLM Router 的统一 LLM 服务。

    内部持有 ``ChatLiteLLMRouter``（LangChain BaseChatModel），
    由 ``litellm.Router`` + ``config.model_list`` 驱动多模型路由。

    所有方法接收 ``list[BaseMessage]``，返回 ``AIMessage`` 或 ``AIMessageChunk``。

    Args:
        config: 应用配置，为 None 时使用全局配置。

    Raises:
        ValueError: ``config.model_list`` 为空时。
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or get_config()
        if not self._config.model_list:
            raise ValueError("config.yaml 中缺少 model_list 配置")
        self._router: Router | None = None
        self._model: ChatLiteLLMRouter | None = None

    # ------------------------------------------------------------------
    # 属性（懒加载）
    # ------------------------------------------------------------------

    @property
    def router(self) -> Router:
        """原始 litellm.Router 实例。"""
        if self._router is None:
            logger.info(
                "构建 LiteLLM Router",
                model_count=len(self._config.model_list),
                default_model=self._config.llm.default_model,
            )
            self._router = Router(model_list=self._config.model_list)
        return self._router

    @property
    def model(self) -> ChatLiteLLMRouter:
        """LangChain BaseChatModel 实例（ChatLiteLLMRouter）。"""
        if self._model is None:
            self._model = ChatLiteLLMRouter(
                router=self.router,
                model=self._config.llm.default_model,
            )
        return self._model

    @property
    def default_model(self) -> str:
        """当前默认模型名。"""
        return self._config.llm.default_model

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def invoke(self, messages: list[BaseMessage], **kwargs: Any) -> AIMessage:
        """同步调用，返回完整 AIMessage（含 usage_metadata / response_metadata / tool_calls）。"""
        return self.model.invoke(messages, **kwargs)

    async def ainvoke(self, messages: list[BaseMessage], **kwargs: Any) -> AIMessage:
        """异步调用，返回完整 AIMessage。"""
        return await self.model.ainvoke(messages, **kwargs)

    def stream(self, messages: list[BaseMessage], **kwargs: Any) -> Iterator[BaseMessage]:
        """同步流式，逐 chunk 产出 AIMessageChunk（含 content / tool_call_chunks / usage_metadata）。"""
        yield from self.model.stream(messages, **kwargs)

    async def astream(self, messages: list[BaseMessage], **kwargs: Any) -> AsyncIterator[BaseMessage]:
        """异步流式，逐 chunk 产出 AIMessageChunk。"""
        async for chunk in self.model.astream(messages, **kwargs):
            yield chunk

    # ------------------------------------------------------------------
    # 工具调用
    # ------------------------------------------------------------------

    def invoke_with_tools(
        self,
        messages: list[BaseMessage],
        tools: list[Any],
        **kwargs: Any,
    ) -> AIMessage:
        """同步调用并绑定工具，返回 AIMessage（含 .tool_calls）。"""
        model_with_tools = self.model.bind_tools(tools)
        return model_with_tools.invoke(messages, **kwargs)

    async def ainvoke_with_tools(
        self,
        messages: list[BaseMessage],
        tools: list[Any],
        **kwargs: Any,
    ) -> AIMessage:
        """异步调用并绑定工具，返回 AIMessage（含 .tool_calls）。"""
        model_with_tools = self.model.bind_tools(tools)
        return await model_with_tools.ainvoke(messages, **kwargs)

    # ------------------------------------------------------------------
    # 观测
    # ------------------------------------------------------------------

    def get_model_names(self) -> list[str]:
        """返回 Router 中配置的全部模型名。"""
        return self.router.get_model_names()

    def count_tokens(self, messages: list[BaseMessage]) -> int:
        """预估给定消息的 token 数（不调用 API）。"""
        from litellm import token_counter

        # token_counter 接受 OpenAI 格式，转换一下
        openai_messages = [{"role": _get_role(m), "content": m.content} for m in messages]
        return token_counter(model=self.default_model, messages=openai_messages)


def _get_role(msg: BaseMessage) -> str:
    """从 BaseMessage 提取 role 字符串。"""
    return msg.type if msg.type in ("human", "ai", "system") else "user"


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_service: LLMService | None = None


def get_llm_service(config: AppConfig | None = None) -> LLMService:
    """获取全局 LLMService 单例。"""
    global _service
    if _service is None:
        _service = LLMService(config)
    return _service


def reset_llm_service() -> None:
    """重置全局单例（测试/热重载用）。"""
    global _service
    _service = None
