from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.data.models.project import Project
from src.data.repositories import ProjectRepository
from src.data.schemas.project import ProjectCreate
from src.data.services.base_service import BaseService


class ProjectService(BaseService[Project, ProjectRepository]):
    def __init__(self, session: Session):
        super().__init__(session, ProjectRepository(session))

    def create_project(self, data: ProjectCreate) -> Project:
        """创建新项目"""
        if self.repo.get_by_name(data.name) is not None:
            raise ValueError(f"项目名称已存在: {data.name}")
        return self.create(Project(**data.model_dump()))

    def list_projects(self, keyword: str | None, status: int | None, page: int, page_size: int):
        filters = []
        if status is not None:
            filters.append(Project.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))
        return self.list(page, page_size, *filters)

    def update_project(self, project_id: int, fields: dict) -> Project:
        if "name" in fields:
            existing = self.repo.get_by_name(fields["name"])
            if existing is not None and existing.id != project_id:
                raise ValueError(f"项目名称已存在: {fields['name']}")
        return self.update(project_id, **fields)

    def delete_project(self, project_id: int) -> None:
        if not self.repo.delete_cascade(project_id):
            raise LookupError("项目不存在")

    def get_project(self, project_id: int) -> Project | None:
        return self.get(project_id)
