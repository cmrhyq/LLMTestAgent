from typing import List

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models import Environment
from src.data.repositories import EnvironmentRepository
from src.data.schemas.environment import EnvironmentCreate

logger = get_logger(__name__)


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
            logger.warning(f"无环境数据需创建", action="create_env")
            return []

        logger.info(f"开始创建环境，数量: {len(env_list)}", action="create_env", count=len(env_list))
        try:
            existing_keys = self._get_existing_keys(env_list)
            new_data = [
                env.model_dump() for env in env_list
                if (env.project_id, env.name) not in existing_keys
            ]
            if not new_data:
                logger.warning(f"所有环境已存在，跳过插入", action="create_env")
                return []
            skipped = len(env_list) - len(new_data)
            if skipped:
                logger.info(f"跳过{skipped}个重复环境", action="create_env", skipped=skipped)
            results = self.repo.bulk_create(new_data)
            logger.info(f"环境创建成功，数量: {len(results)}", action="create_env", created=len(results))
            return results
        except Exception as e:
            logger.error(f"环境创建失败: {e}", action="create_env", error=str(e))
            raise