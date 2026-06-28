from types import TracebackType
from typing import Protocol, Self

from academic_os.application.ports.repositories import Repository
from academic_os.domain import (
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


class UnitOfWork(Protocol):
    """Transaction boundary and repository access contract."""

    institutions: Repository[Institution]
    degrees: Repository[Degree]
    academic_years: Repository[AcademicYear]
    semesters: Repository[Semester]
    courses: Repository[Course]
    degree_courses: Repository[DegreeCourse]
    curriculum_items: Repository[CurriculumItem]
    study_plans: Repository[StudyPlan]
    study_plan_items: Repository[StudyPlanItem]
    study_tasks: Repository[StudyTask]
    study_sessions: Repository[StudySession]
    study_progress: Repository[StudyProgress]
    events: Repository[Event]
    notes: Repository[Note]
    assignments: Repository[Assignment]
    exams: Repository[Exam]

    def __enter__(self) -> Self:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

