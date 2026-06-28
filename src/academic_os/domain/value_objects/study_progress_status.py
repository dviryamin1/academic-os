from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class StudyProgressStatus:
    NOT_STARTED: ClassVar[str] = "not_started"
    IN_PROGRESS: ClassVar[str] = "in_progress"
    MASTERED: ClassVar[str] = "mastered"

    code: str
