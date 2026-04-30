from typing import TypeVar, List

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models import Environment
from src.data.models.base import Base
from src.data.repositories import EnvironmentRepository
from src.data.schemas.environment import EnvironmentCreate

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class EnvironmentService:
    def __init__(self, session: Session):
        self.repo = EnvironmentRepository(session)

    def _get_existing_keys(self, env_list: List[EnvironmentCreate]) -> set:
        """批量查询已存在的 (project_id, name) 组合"""
        project_ids = {env.project_id for env in env_list}
        names = {env.name for env in env_list}
        existing = self.repo.bulk_query(project_ids, names)
        return {(item.project_id, item.name) for item in existing}

    def create_env(self, env_list: List[EnvironmentCreate]) -> List[Environment]:
        """
        去重批量创建环境
        """
        if len(env_list) == 0:
            logger.warning("No environments to create")
            return []

        logger.info(f"Creating {len(env_list)} environments")
        try:
            # 1. 批量查询已存在的记录（一次查询代替 N 次）
            existing_keys = self._get_existing_keys(env_list)
            # 2. 过滤掉重复数据
            new_data = [
                env.model_dump() for env in env_list
                if (env.project_id, env.name) not in existing_keys
            ]
            if not new_data:
                logger.warning("All environments already exist, skip insert")
                return []
            skipped = len(env_list) - len(new_data)
            if skipped:
                logger.info(f"Skipped {skipped} duplicate environments")
            # 3. 批量插入
            results = self.repo.bulk_create(new_data)
            logger.info(f"Successfully created {len(results)} environments")
            return results
        except Exception as e:
            logger.error(f"Failed to create environments: {e}")
            raise