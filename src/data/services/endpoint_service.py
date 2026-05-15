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
        """批量查询已存在的 (project_id, path, method) 组合"""
        project_ids = {endpoint.project_id for endpoint in endpoint_list}
        paths = {endpoint.path for endpoint in endpoint_list}
        methods = {endpoint.method for endpoint in endpoint_list}
        existing = self.repo.bulk_query(project_ids, paths, methods)
        return {(item.project_id, item.path, item.method) for item in existing}

    def create_endpoint(self, endpoints: List[EndpointCreate]) -> List[Endpoint]:
        if len(endpoints) == 0:
            logger.warning("无接口数据需创建")
            return []

        logger.info("开始创建接口", count=len(endpoints))

        try:
            existing_keys = self._get_existing_keys(endpoints)
            logger.debug("已存在记录查询完成", existing_count=len(existing_keys))
            new_data = [
                endpoint.model_dump() for endpoint in endpoints
                if (endpoint.project_id, endpoint.path, endpoint.method) not in existing_keys
            ]
            if not new_data:
                logger.warning("所有接口已存在，跳过插入")
                return []
            skipped = len(endpoints) - len(new_data)
            if skipped:
                logger.info("跳过重复接口", skipped=skipped)
            results = self.repo.bulk_create(new_data)
            logger.info("接口创建成功", created=len(results))
            return results
        except Exception as e:
            logger.error("接口创建失败", error=str(e))
            raise
