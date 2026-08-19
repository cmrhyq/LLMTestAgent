from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.data.models.project import Project
from src.data.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """项目表数据访问"""

    def __init__(self, session: Session) -> None:
        super().__init__(Project, session)

    def get_by_name(self, name: str) -> Project | None:
        stmt = select(Project).where(Project.name == name)
        return self._session.scalar(stmt)

    def delete_cascade(self, project_id: int) -> bool:
        """级联删除项目及其关联的 environments、endpoints、test_runs 等数据。"""
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.endpoints),
                selectinload(Project.environments),
                selectinload(Project.test_runs),
            )
        )
        project = self._session.scalar(stmt)
        if project is None:
            return False
        self._session.delete(project)
        self._session.flush()
        return True
