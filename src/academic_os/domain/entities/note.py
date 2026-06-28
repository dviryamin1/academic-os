from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Note:
    id: UUID
    curriculum_item_id: UUID
    content: str
    created_at: datetime

