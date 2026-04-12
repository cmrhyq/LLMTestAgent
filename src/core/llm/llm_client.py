"""
LLM客户端模块

提供统一的LLM调用接口，支持多种LLM提供商：
- OpenAI
- AWS Bedrock
- 智谱AI
- 通义千问
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from src.core.config import get_config, AppConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient(ABC):
    """
    LLM客户端抽象基类
    """
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
            **kwargs: 其他参数
            
        Returns:
            str: LLM响应内容
        """
        pass
    
    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """
        获取LangChain模型实例
        
        Returns:
            BaseChatModel: LangChain模型
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI客户端"""
    
    def __init__(self, config: AppConfig):
        """
        初始化OpenAI客户端
        
        Args:
            config: 应用配置
        """
        self.config = config.llm.openai
        self._model: Optional[BaseChatModel] = None
    
    def get_model(self) -> BaseChatModel:
        """获取LangChain OpenAI模型"""
        if self._model is None:
            from langchain_openai import ChatOpenAI
            self._model = ChatOpenAI(
                api_key=self.config.api_key,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        return self._model
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        model = self.get_model()
        langchain_messages = self._convert_messages(messages)
        response = model.invoke(langchain_messages)
        return response.content
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """转换消息格式"""
        result = []
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


class BedrockClient(LLMClient):
    """AWS Bedrock客户端"""
    
    def __init__(self, config: AppConfig):
        """
        初始化Bedrock客户端
        
        Args:
            config: 应用配置
        """
        self.config = config.llm.bedrock
        self._model: Optional[BaseChatModel] = None
        self._fallback_model: Optional[BaseChatModel] = None
    
    def _create_bedrock_runtime_client(self):
        """创建Bedrock Runtime客户端，支持临时凭证session token。"""
        import boto3
        return boto3.client(
            "bedrock-runtime",
            region_name=self.config.region,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            aws_session_token=self.config.session_token or None,
        )
    
    def get_model(self) -> BaseChatModel:
        """获取LangChain Bedrock模型"""
        if self._model is None:
            from langchain_aws import ChatBedrock
            bedrock_client = self._create_bedrock_runtime_client()
            
            self._model = ChatBedrock(
                client=bedrock_client,
                model_id=self.config.model_id,
                model_kwargs={"max_tokens": self.config.max_tokens},
            )
        return self._model
    
    def _get_fallback_model(self) -> Optional[BaseChatModel]:
        """
        获取回退模型（移除 us./eu./apac. 区域前缀后重试）。
        
        某些 Bedrock SDK/适配层会错误识别带区域前缀的模型为非 chat 模型。
        """
        model_id = self.config.model_id
        prefixes = ("us.", "eu.", "apac.")
        matched_prefix = next((prefix for prefix in prefixes if model_id.startswith(prefix)), None)
        if matched_prefix is None:
            return None
        
        fallback_model_id = model_id[len(matched_prefix):]
        if not fallback_model_id:
            return None
        
        if self._fallback_model is None:
            from langchain_aws import ChatBedrock
            bedrock_client = self._create_bedrock_runtime_client()
            self._fallback_model = ChatBedrock(
                client=bedrock_client,
                model_id=fallback_model_id,
                model_kwargs={"max_tokens": self.config.max_tokens},
            )
            logger.warning(
                f"Bedrock模型[{model_id}]调用失败，尝试回退模型ID: {fallback_model_id}"
            )
        
        return self._fallback_model
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        model = self.get_model()
        langchain_messages = self._convert_messages(messages)
        try:
            response = model.invoke(langchain_messages)
            return response.content
        except Exception as e:
            error_message = str(e)
            normalized_message = error_message.lower()
            if "unrecognizedclientexception" in normalized_message or "security token included in the request is invalid" in normalized_message:
                raise RuntimeError(
                    "AWS凭证无效：请检查 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY，"
                    "如果使用临时凭证还需要设置 AWS_SESSION_TOKEN。"
                ) from e
            if "does not support chat" in error_message.lower():
                fallback_model = self._get_fallback_model()
                if fallback_model is not None:
                    response = fallback_model.invoke(langchain_messages)
                    return response.content
            raise
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """转换消息格式"""
        result = []
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


class ZhipuClient(LLMClient):
    """智谱AI客户端"""
    
    def __init__(self, config: AppConfig):
        """
        初始化智谱AI客户端
        
        Args:
            config: 应用配置
        """
        self.config = config.llm.zhipu
        self._model: Optional[BaseChatModel] = None
    
    def get_model(self) -> BaseChatModel:
        """获取LangChain智谱模型"""
        if self._model is None:
            from langchain_community.chat_models import ChatZhipuAI
            self._model = ChatZhipuAI(
                api_key=self.config.api_key,
                model=self.config.model,
            )
        return self._model
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        model = self.get_model()
        langchain_messages = self._convert_messages(messages)
        response = model.invoke(langchain_messages)
        return response.content
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """转换消息格式"""
        result = []
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


class QwenClient(LLMClient):
    """通义千问客户端"""
    
    def __init__(self, config: AppConfig):
        """
        初始化通义千问客户端
        
        Args:
            config: 应用配置
        """
        self.config = config.llm.qwen
        self._model: Optional[BaseChatModel] = None
    
    def get_model(self) -> BaseChatModel:
        """获取LangChain通义千问模型"""
        if self._model is None:
            from langchain_community.chat_models import ChatTongyi
            self._model = ChatTongyi(
                dashscope_api_key=self.config.api_key,
                model=self.config.model,
            )
        return self._model
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """发送聊天请求"""
        model = self.get_model()
        langchain_messages = self._convert_messages(messages)
        response = model.invoke(langchain_messages)
        return response.content
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List:
        """转换消息格式"""
        result = []
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


def create_llm_client(config: Optional[AppConfig] = None) -> LLMClient:
    """
    创建LLM客户端
    
    根据配置创建对应的LLM客户端实例。
    
    Args:
        config: 应用配置，如果为None则使用全局配置
        
    Returns:
        LLMClient: LLM客户端实例
    """
    if config is None:
        config = get_config()
    
    provider = config.llm.provider.lower()
    
    if provider == "openai":
        logger.info("使用OpenAI作为LLM提供商")
        return OpenAIClient(config)
    elif provider == "bedrock":
        logger.info("使用AWS Bedrock作为LLM提供商")
        return BedrockClient(config)
    elif provider == "zhipu":
        logger.info("使用智谱AI作为LLM提供商")
        return ZhipuClient(config)
    elif provider == "qwen":
        logger.info("使用通义千问作为LLM提供商")
        return QwenClient(config)
    else:
        logger.warning(f"未知的LLM提供商: {provider}, 使用OpenAI作为默认")
        return OpenAIClient(config)


# 全局LLM客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    获取全局LLM客户端实例
    
    Returns:
        LLMClient: LLM客户端实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = create_llm_client()
    return _llm_client


def init_llm_client(config: Optional[AppConfig] = None) -> LLMClient:
    """
    初始化LLM客户端
    
    Args:
        config: 应用配置
        
    Returns:
        LLMClient: LLM客户端实例
    """
    global _llm_client
    _llm_client = create_llm_client(config)
    return _llm_client
