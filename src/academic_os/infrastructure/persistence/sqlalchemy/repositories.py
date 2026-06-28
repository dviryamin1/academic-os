from typing import Generic
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from academic_os.infrastructure.persistence.sqlalchemy.mappers import (
    DomainT,
    EntityMapper,
    ModelT,
)


class SqlAlchemyRepository(Generic[DomainT, ModelT]):
    """SQLAlchemy adapter for the repository persistence contract."""

    def __init__(
        self,
        session: Session,
        mapper: EntityMapper[DomainT, ModelT],
    ) -> None:
        self._session = session
        self._mapper = mapper

    def add(self, entity: DomainT) -> None:
        self._session.add(self._mapper.to_model(entity))

    def update(self, entity: DomainT) -> None:
        self._session.merge(self._mapper.to_model(entity))

    def get(self, entity_id: UUID) -> DomainT | None:
        model = self._session.get(self._mapper.model_type, entity_id)
        return None if model is None else self._mapper.to_domain(model)

    def list_all(self) -> list[DomainT]:
        statement = select(self._mapper.model_type)
        models = self._session.scalars(statement).all()
        return [self._mapper.to_domain(model) for model in models]

    def remove(self, entity_id: UUID) -> bool:
        model = self._session.get(self._mapper.model_type, entity_id)
        if model is None:
            return False

        self._session.delete(model)
        return True
