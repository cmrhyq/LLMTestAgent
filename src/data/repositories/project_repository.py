from typing import Optional, List, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.enum.workflow import DataStatus
from src.data.models.base import Base
from src.data.models.project import Project

from src.core.logging import get_logger
from src.data.repositories.base import BaseRepository


logger = get_logger(__name__)
T = TypeVar("T", bound=Base)


class ProjectRepository(BaseRepository[Project]):
    """项目表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Project, session)

    def get_by_name(self, name: str) -> Optional[Project]:
        stmt = select(Project).where(Project.name == name)
        return self._session.scalar(stmt)

    def get_active_projects(self) -> List[Project]:
        stmt = select(Project).where(Project.status == DataStatus.ENABLE.value)
        return list(self._session.scalars(stmt).all())

    def find_or_create(self, name: str, base_url: str, description: str = "") -> Project:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        project = Project(name=name, base_url=base_url, description=description)
        return self.add(project)
