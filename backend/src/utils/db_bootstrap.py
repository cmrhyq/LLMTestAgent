"""数据库初始化引导工具。

供 graph 节点等非 Web 场景在使用数据库前确保连接已初始化。
"""

from src.core.config import get_config
from src.core.database.connection import get_db_manager


def ensure_db() -> None:
    """确保数据库已初始化（幂等）。"""
    manager = get_db_manager()
    if not manager.is_initialized:
        config = get_config()
        manager.initialize(
            db_url=config.database.url,
            echo=config.database.echo,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_timeout=config.database.pool_timeout,
            pool_recycle=config.database.pool_recycle,
        )
