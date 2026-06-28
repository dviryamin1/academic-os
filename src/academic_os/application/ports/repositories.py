from typing import Protocol, TypeVar
from uuid import UUID

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    """Persistence operations available for one domain entity type."""

    def add(self, entity: EntityT) -> None:
        ...

    def update(self, entity: EntityT) -> None:
        ...

    def get(self, entity_id: UUID) -> EntityT | None:
        ...

    def list_all(self) -> list[EntityT]:
        ...

    def remove(self, entity_id: UUID) -> bool:
        ...
