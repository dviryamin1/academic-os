from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from academic_os.domain.value_objects import StudyTaskType


@dataclass(frozen=True, slots=True, kw_only=True)
class StudyTask:
    id: UUID
    curriculum_item_id: UUID
    task_type: StudyTaskType
    title: str
    due_at: datetime | None
    completed_at: datetime | None

