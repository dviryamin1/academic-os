from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StudySession:
    id: UUID
    curriculum_item_id: UUID
    started_at: datetime
    ended_at: datetime | None

