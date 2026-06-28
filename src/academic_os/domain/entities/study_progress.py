from dataclasses import dataclass
from uuid import UUID

from academic_os.domain.value_objects import StudyProgressStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class StudyProgress:
    id: UUID
    curriculum_item_id: UUID
    status: StudyProgressStatus

