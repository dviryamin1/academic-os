from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class StudyTaskType:
    READING: ClassVar[str] = "reading"
    SUMMARY: ClassVar[str] = "summary"
    PRACTICE: ClassVar[str] = "practice"
    REVIEW: ClassVar[str] = "review"
    SELF_TEST: ClassVar[str] = "self_test"

    code: str
