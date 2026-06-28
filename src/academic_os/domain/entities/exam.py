from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Exam:
    id: UUID
    course_id: UUID
    title: str
    starts_at: datetime

