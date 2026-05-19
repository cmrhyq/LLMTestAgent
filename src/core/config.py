"""
配置管理模块

负责加载和管理应用配置，支持从YAML文件和环境变量读取配置。
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import yaml

logger = logging.getLogger(__name__)
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")


class OpenAIConfig(BaseModel):
    """OpenAI配置"""
    api_key: str = Field(default="", description="OpenAI API密钥")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")


class BedrockConfig(BaseModel):
    """AWS Bedrock配置"""
    region: str = Field(default="us-east-1", description="AWS区域")
    model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", description="模型ID")
    max_tokens: int = Field(default=4096, description="最大token数")
    access_key: str = Field(default="", description="AWS Access Key")
    secret_key: str = Field(default="", description="AWS Secret Key")
    session_token: str = Field(default="", description="AWS Session Token（临时凭证必填）")


class ZhipuConfig(BaseModel):
    """智谱AI配置"""
    api_key: str = Field(default="", description="智谱API密钥")
    model: str = Field(default="glm-4", description="模型名称")


class QwenConfig(BaseModel):
    """通义千问配置"""
    api_key: str = Field(default="", description="通义千问API密钥")
    model: str = Field(default="qwen-max", description="模型名称")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    zhipu: ZhipuConfig = Field(default_factory=ZhipuConfig)
    qwen: QwenConfig = Field(default_factory=QwenConfig)


class RetryConfig(BaseModel):
    """重试配置"""
    max_retries: int = Field(default=2, description="最大重试次数")
    retry_interval: float = Field(default=1.0, description="重试间隔（秒）")
    retry_on_status: List[int] = Field(default=[500, 502, 503, 504], description="需要重试的状态码")


class ConcurrencyConfig(BaseModel):
    """并发配置"""
    enabled: bool = Field(default=True, description="是否启用并发")
    max_workers: int = Field(default=5, description="最大并发数")


class ExecutionConfig(BaseModel):
    """测试执行配置"""
    connect_timeout: int = Field(default=5, description="连接超时（秒）")
    read_timeout: int = Field(default=30, description="读取超时（秒）")
    total_timeout: int = Field(default=60, description="总超时（秒）")
    retry: RetryConfig = Field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    dependency_failure: str = Field(default="skip", description="依赖失败处理方式")


class OutputConfig(BaseModel):
    """输出配置"""
    base_dir: str = Field(default="output", description="输出根目录")
    test_cases_dir: str = Field(default=f"output/{timestamp}/test_cases", description="用例目录")
    reports_dir: str = Field(default=f"output/{timestamp}/reports", description="报告目录")


class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field(default="sqlite:///db/LLMTest.db", description="数据库连接URL")
    echo: bool = Field(default=False, description="是否输出SQL语句")
    pool_size: int = Field(default=5, description="连接池大小")
    max_overflow: int = Field(default=10, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接池获取超时（秒）")
    pool_recycle: int = Field(default=3600, description="连接回收时间（秒）")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="console", description="输出格式: console(彩色) / json(生产环境)")
    debug: bool = Field(default=False, deprecated="debug参数已废弃，请使用format字段", description="调试模式(已废弃)")


class AppConfig(BaseModel):
    """应用配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def _resolve_env_vars(value: Any) -> Any:
    """
    递归解析配置值中的环境变量
    
    Args:
        value: 配置值
        
    Returns:
        解析后的值
    """
    load_dotenv()
    if isinstance(value, str):
        # 解析 ${VAR_NAME} 格式的环境变量
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, "")
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载应用配置
    
    Args:
        config_path: 配置文件路径，默认为 config/config.yaml
        
    Returns:
        AppConfig: 应用配置对象
    """
    if config_path is None:
        # 默认配置文件路径
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)
    
    config_data = {}
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
            # 解析环境变量
            config_data = _resolve_env_vars(config_data)
            logger.info("配置文件加载成功: %s", config_path)
        except Exception as e:
            logger.warning(f"配置文件加载失败，使用默认配置, error: {e}", exc_info=e)
    else:
        logger.warning("配置文件不存在: %s，使用默认配置", config_path)
    
    return AppConfig(**config_data)


def ensure_output_dirs(config: AppConfig) -> None:
    """
    确保输出目录存在
    
    Args:
        config: 应用配置
    """
    dirs = [
        config.output.base_dir,
        config.output.test_cases_dir,
        config.output.reports_dir,
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.debug("输出目录已确认: %s", dir_path)


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    获取全局配置实例
    
    Returns:
        AppConfig: 应用配置对象
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def init_config(config_path: Optional[str] = None) -> AppConfig:
    """
    初始化配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        AppConfig: 应用配置对象
    """
    global _config
    _config = load_config(config_path)
    ensure_output_dirs(_config)
    return _config
