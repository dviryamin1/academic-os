from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StudyPlan:
    id: UUID
    semester_id: UUID

