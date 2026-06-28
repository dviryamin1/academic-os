from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Course:
    id: UUID
    institution_id: UUID
    code: str
    title: str

