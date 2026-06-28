from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StudyPlanItem:
    id: UUID
    study_plan_id: UUID
    curriculum_item_id: UUID

