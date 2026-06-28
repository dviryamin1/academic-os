from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class AcademicYear:
    id: UUID
    degree_id: UUID
    label: str
    start_date: date
    end_date: date

