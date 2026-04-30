from typing import TypeVar, List

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.data.models import Endpoint
from src.data.models.base import Base
from src.data.repositories import EndpointRepository
from src.data.schemas.endpoint import EndpointCreate

logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class EndpointService:
    def __init__(self, session: Session):
        self.repo = EndpointRepository(session)

    def _get_existing_keys(self, endpoint_list: List[EndpointCreate]) -> set:
        """批量查询已存在的 (project_id, name) 组合"""
        project_ids = {endpoint.project_id for endpoint in endpoint_list}
        paths = {endpoint.path for endpoint in endpoint_list}
        methods = {endpoint.method for endpoint in endpoint_list}
        existing = self.repo.bulk_query(project_ids, paths, methods)
        return {(item.project_id, item.name) for item in existing}

    def create_endpoint(self, endpoints: List[EndpointCreate]) -> List[Endpoint]:
        if len(endpoints) == 0:
            logger.warning("No endpoints to create")
            return []

        logger.info(f"Creating {len(endpoints)} endpoints")

        try:
            # 1. 批量查询已存在的记录（一次查询代替 N 次）
            existing_keys = self._get_existing_keys(endpoints)
            # 2. 过滤掉重复数据
            new_data = [
                endpoint.model_dump() for endpoint in endpoints
                if (endpoint.project_id, endpoint.path, endpoint.method) not in existing_keys
            ]
            if not new_data:
                logger.warning("All endpoints already exist, skip insert")
                return []
            skipped = len(endpoints) - len(new_data)
            if skipped:
                logger.info(f"Skipped {skipped} duplicate endpoints")
            # 3. 批量插入
            results = self.repo.bulk_create(new_data)
            logger.info(f"Successfully created {len(results)} endpoints")
            return results
        except Exception as e:
            logger.error(f"Failed to create endpoints: {e}")
            raise
