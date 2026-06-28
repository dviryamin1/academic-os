"""Framework-independent domain model."""

from academic_os.domain.entities import (
    AcademicYear,
    Assignment,
    Course,
    CurriculumItem,
    Degree,
    DegreeCourse,
    Event,
    Exam,
    Institution,
    Note,
    Semester,
    StudyPlan,
    StudyPlanItem,
    StudyProgress,
    StudySession,
    StudyTask,
)
from academic_os.domain.value_objects import (
    CurriculumItemType,
    StudyProgressStatus,
    StudyTaskType,
)

__all__ = [
    "AcademicYear",
    "Assignment",
    "Course",
    "CurriculumItem",
    "CurriculumItemType",
    "Degree",
    "DegreeCourse",
    "Event",
    "Exam",
    "Institution",
    "Note",
    "Semester",
    "StudyPlan",
    "StudyPlanItem",
    "StudyProgress",
    "StudyProgressStatus",
    "StudySession",
    "StudyTask",
    "StudyTaskType",
]
