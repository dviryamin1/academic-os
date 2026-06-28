from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class DegreeCourse:
    id: UUID
    degree_id: UUID
    course_id: UUID
    credits: Decimal | None

