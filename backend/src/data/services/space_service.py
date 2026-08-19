from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.core.errors import ConflictError, NotFoundError
from src.data.models.space import Space
from src.data.repositories import SpaceRepository
from src.data.schemas.space import SpaceCreate
from src.data.services.base_service import BaseService


class SpaceService(BaseService[Space, SpaceRepository]):
    def __init__(self, session: Session):
        super().__init__(session, SpaceRepository(session))

    def create_space(self, data: SpaceCreate) -> Space:
        """创建新空间"""
        if self.repo.get_by_name(data.name) is not None:
            raise ConflictError(f"空间名称已存在: {data.name}")
        return self.create(Space(**data.model_dump()))

    def list_spaces(self, keyword: str | None, status: int | None, page: int, page_size: int):
        filters = []
        if status is not None:
            filters.append(Space.status == status)
        if keyword:
            pattern = f"%{keyword}%"
            filters.append(or_(Space.name.ilike(pattern), Space.description.ilike(pattern)))
        return self.list(page, page_size, *filters)

    def update_space(self, space_id: int, fields: dict) -> Space:
        if "name" in fields:
            existing = self.repo.get_by_name(fields["name"])
            if existing is not None and existing.id != space_id:
                raise ConflictError(f"空间名称已存在: {fields['name']}")
        return self.update(space_id, **fields)

    def delete_space(self, space_id: int) -> None:
        if not self.repo.delete_cascade(space_id):
            raise NotFoundError("空间不存在")

    def get_space(self, space_id: int) -> Space | None:
        return self.get(space_id)
