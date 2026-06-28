from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Semester:
    id: UUID
    academic_year_id: UUID
    name: str
    start_date: date
    end_date: date
