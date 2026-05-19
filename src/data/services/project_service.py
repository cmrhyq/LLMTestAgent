from sqlalchemy.orm import Session

from src.data.models.project import Project
from src.data.repositories import ProjectRepository
from src.data.schemas.project import ProjectCreate


class ProjectService:
    def __init__(self, session: Session):
        self.repo = ProjectRepository(session)

    def create_project(self, data: ProjectCreate) -> Project:
        """创建新项目"""
        return self.repo.find_or_create(data.name, data.base_url, data.description)
