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
            logger.warning(f"无接口数据需创建", action="create_endpoint")
            return []

        logger.info(f"开始创建接口，数量: {len(endpoints)}", action="create_endpoint", count=len(endpoints))

        try:
            existing_keys = self._get_existing_keys(endpoints)
            logger.debug(f"已存在记录查询完成，重复数: {len(existing_keys)}", action="create_endpoint", existing_count=len(existing_keys))
            new_data = [
                endpoint.model_dump() for endpoint in endpoints
                if (endpoint.project_id, endpoint.path, endpoint.method) not in existing_keys
            ]
            if not new_data:
                logger.warning(f"所有接口已存在，跳过插入", action="create_endpoint")
                return []
            skipped = len(endpoints) - len(new_data)
            if skipped:
                logger.info(f"跳过{skipped}个重复接口", action="create_endpoint", skipped=skipped)
            results = self.repo.bulk_create(new_data)
            logger.info(f"接口创建成功，数量: {len(results)}", action="create_endpoint", created=len(results))
            return results
        except Exception as e:
            logger.error(f"接口创建失败: {e}", action="create_endpoint", error=str(e))
            raise
