"""LLM 模型工厂模块。

提供统一的工厂函数，根据配置返回对应的 LangChain BaseChatModel 实例。
支持 OpenAI、AWS Bedrock、智谱AI、通义千问。
"""

import time
from typing import List, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from src.core.config import get_config, AppConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_chat_model(config: Optional[AppConfig] = None) -> BaseChatModel:
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
        logger.info("LLM提供商初始化", provider="OpenAI")
        return _create_openai_model(config)
    elif provider == "bedrock":
        logger.info("LLM提供商初始化", provider="AWS Bedrock")
        return _create_bedrock_model(config)
    elif provider == "zhipu":
        logger.info("LLM提供商初始化", provider="智谱AI")
        return _create_zhipu_model(config)
    elif provider == "qwen":
        logger.info("LLM提供商初始化", provider="通义千问")
        return _create_qwen_model(config)
    else:
        logger.warning("未知的LLM提供商，使用OpenAI作为默认", provider=provider)
        return _create_openai_model(config)


def _create_openai_model(config: AppConfig) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    openai_config = config.llm.openai
    return ChatOpenAI(
        api_key=openai_config.api_key,
        model=openai_config.model,
        temperature=openai_config.temperature,
        max_tokens=openai_config.max_tokens,
    )


def _create_bedrock_model(config: AppConfig) -> BaseChatModel:
    import boto3
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
        model_id=bedrock_config.model_id,
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
        dashscope_api_key=qwen_config.api_key,
        model=qwen_config.model,
    )


def convert_to_langchain_messages(messages: List[Dict[str, str]]) -> List[BaseMessage]:
    """将字典格式消息列表转换为 LangChain BaseMessage 列表。

    Args:
        messages: [{"role": "system/user/assistant", "content": "..."}]

    Returns:
        LangChain 消息列表
    """
    result: List[BaseMessage] = []
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

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求，返回纯文本响应。"""
        logger.debug("LLM调用开始", message_count=len(messages))
        start_time = time.perf_counter()
        langchain_messages = convert_to_langchain_messages(messages)
        response = self._model.invoke(langchain_messages)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug("LLM调用完成", elapsed_ms=elapsed_ms, response_length=len(response.content))
        return response.content

    def invoke_with_tools(
        self,
        messages: List[BaseMessage],
        tools,
        **kwargs,
    ) -> BaseMessage:
        """使用已转换的消息发送带工具绑定的请求。"""
        model_with_tools = self._model.bind_tools(tools)
        return model_with_tools.invoke(messages)

    def get_model(self) -> BaseChatModel:
        return self._model

    @staticmethod
    def _convert_messages_base(messages: List[Dict[str, str]]) -> List[BaseMessage]:
        return convert_to_langchain_messages(messages)


_chat_model: Optional[BaseChatModel] = None
_llm_client: Optional[LLMClient] = None


def get_chat_model(config: Optional[AppConfig] = None) -> BaseChatModel:
    """获取全局 ChatModel 单例。"""
    global _chat_model
    if _chat_model is None:
        _chat_model = create_chat_model(config)
    return _chat_model


def get_llm_client(config: Optional[AppConfig] = None) -> LLMClient:
    """获取全局 LLMClient 单例（兼容旧接口）。"""
    global _llm_client
    if _llm_client is None:
        model = get_chat_model(config)
        _llm_client = LLMClient(model)
    return _llm_client


def init_llm_client(config: Optional[AppConfig] = None) -> LLMClient:
    """重新初始化全局 LLM 客户端。"""
    global _chat_model, _llm_client
    _chat_model = create_chat_model(config)
    _llm_client = LLMClient(_chat_model)
    return _llm_client
