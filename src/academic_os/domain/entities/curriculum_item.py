from dataclasses import dataclass
from uuid import UUID

from academic_os.domain.value_objects import CurriculumItemType


@dataclass(frozen=True, slots=True, kw_only=True)
class CurriculumItem:
    id: UUID
    code: str
    parent_id: UUID | None
    title: str
    item_type: CurriculumItemType
    course_id: UUID
    source: str | None
    pages: str | None
    order: int
