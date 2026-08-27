"""LiteLLM Router 客户端。

Router 的 ``model_list`` 不再硬编码，改为从 ``config/config.yaml`` 的
``model_list`` 块读取（经 ``src.core.config`` 加载，密钥可在 YAML 中用
``${ENV_VAR}`` 占位，避免明文落库）。
"""

import asyncio
import logging

from litellm import Router

from src.core.config import get_config

logger = logging.getLogger(__name__)


def create_router() -> Router:
    """从全局配置构建 LiteLLM Router。

    Returns:
        Router: 基于 ``config.model_list`` 构建的路由器

    Raises:
        ValueError: 配置中不存在 model_list
    """
    config = get_config()
    if not config.model_list:
        raise ValueError("config.yaml 中缺少 model_list 配置，无法构建 LiteLLM Router")

    logger.info("LiteLLM Router 初始化，模型数量: %d", len(config.model_list))
    router = Router(model_list=config.model_list)
    return router


# 全局 Router 单例（惰性创建，配置初始化后首次调用生效）
_router: Router | None = None


def get_router() -> Router:
    """获取全局 Router 单例。"""
    global _router
    if _router is None:
        _router = create_router()
    return _router


async def main():
    """示例：使用 smart-router 按提示词复杂度分流（应用层实现）。"""
    router = get_router()

    response1 = await router.acompletion(
        model="smart-router",
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print(response1)

    response2 = await router.acompletion(
        model="smart-router",
        messages=[{"role": "user",
                   "content": "Design a distributed microservice architecture with Kubernetes orchestration"}],
    )
    print(response2)

    response3 = await router.acompletion(
        model="smart-router",
        messages=[{"role": "user", "content": "Think step by step and reason through this problem carefully..."}],
    )
    print(response3)


if __name__ == "__main__":
    asyncio.run(main())
