from typing import Optional, List, TypeVar, Type, Generic

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.data.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """通用 CRUD 基类"""

    def __init__(self, model_class: Type[T], session: Session) -> None:
        self._model = model_class
        self._session = session

    def get_by_id(self, record_id: int) -> Optional[T]:
        return self._session.get(self._model, record_id)

    def get_all(self, limit: int = 1000, offset: int = 0) -> List[T]:
        stmt = select(self._model).limit(limit).offset(offset)
        return list(self._session.scalars(stmt).all())

    def add(self, entity: T) -> T:
        self._session.add(entity)
        self._session.flush()
        return entity

    def add_many(self, entities: List[T]) -> List[T]:
        self._session.add_all(entities)
        self._session.flush()
        return entities

    def update_entity(self, entity: T) -> T:
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def delete_by_id(self, record_id: int) -> bool:
        entity = self.get_by_id(record_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.flush()
        return True

    def bulk_create(self, objects: list[dict]) -> List[T]:
        db_objects = [self._model(**obj) for obj in objects]
        self._session.add_all(db_objects)
        self._session.flush()
        for obj in db_objects:
            self._session.refresh(obj)
        return db_objects

    def count(self) -> int:
        stmt = select(func.count()).select_from(self._model)
        return self._session.scalar(stmt) or 0