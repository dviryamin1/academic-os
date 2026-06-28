from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None

