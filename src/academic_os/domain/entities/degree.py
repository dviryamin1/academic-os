from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Degree:
    id: UUID
    institution_id: UUID
    name: str

