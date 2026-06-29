from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from academic_os.application.ports import UnitOfWork
from academic_os.domain import (
    Course,
    CurriculumItem,
    StudyProgress,
    StudyProgressStatus,
    StudySession,
    StudyTask,
    StudyTaskType,
)

UnitOfWorkFactory = Callable[[], UnitOfWork]
TASK_TYPE_PRIORITY = {
    StudyTaskType.READING: 0,
    StudyTaskType.SUMMARY: 1,
    StudyTaskType.PRACTICE: 2,
    StudyTaskType.REVIEW: 3,
}


@dataclass(frozen=True, slots=True)
class ResumeLearning:
    item: CurriculumItem
    course: Course
    last_activity_at: datetime
    last_session_duration_minutes: int | None
    progress_status: StudyProgressStatus
    open_tasks: tuple[StudyTask, ...]


@dataclass(frozen=True, slots=True)
class NextStudyRecommendation:
    task: StudyTask
    item: CurriculumItem
    course: Course
    reason: str


@dataclass(frozen=True, slots=True)
class OpenTask:
    task: StudyTask
    item: CurriculumItem
    course: Course


@dataclass(frozen=True, slots=True)
class CourseProgressSummary:
    course: Course
    total_items: int
    not_started_items: int
    in_progress_items: int
    mastered_items: int
    open_tasks: int
    completed_tasks: int
    total_study_minutes: int


@dataclass(frozen=True, slots=True)
class _StudyData:
    courses: tuple[Course, ...]
    items: tuple[CurriculumItem, ...]
    tasks: tuple[StudyTask, ...]
    sessions: tuple[StudySession, ...]
    progress: tuple[StudyProgress, ...]


class StudyWorkflowService:
    """Provides read-oriented workflows for deciding what to study."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def resume_learning(self) -> ResumeLearning | None:
        return self._resume_from_data(self._load_data())

    def recommend_next(self) -> NextStudyRecommendation | None:
        data = self._load_data()
        open_tasks = [task for task in data.tasks if task.completed_at is None]
        if not open_tasks:
            return None

        resume = self._resume_from_data(data)
        if resume is not None:
            resume_tasks = [
                task
                for task in open_tasks
                if task.curriculum_item_id == resume.item.id
            ]
            if resume_tasks:
                task = min(resume_tasks, key=_task_priority_key)
                return NextStudyRecommendation(
                    task=task,
                    item=resume.item,
                    course=resume.course,
                    reason="Continue the item you studied most recently.",
                )

        items_by_id = {item.id: item for item in data.items}
        courses_by_id = {course.id: course for course in data.courses}
        task = min(
            open_tasks,
            key=lambda candidate: (
                _curriculum_order_key(
                    items_by_id[candidate.curriculum_item_id],
                    items_by_id,
                    courses_by_id,
                ),
                _task_priority_key(candidate),
            ),
        )
        item = items_by_id[task.curriculum_item_id]
        return NextStudyRecommendation(
            task=task,
            item=item,
            course=courses_by_id[item.course_id],
            reason=(
                f"This is the earliest open {task.task_type.code} task "
                "in your curriculum."
            ),
        )

    def list_open_tasks(self, course_query: str | None = None) -> list[OpenTask]:
        data = self._load_data()
        courses = data.courses
        selected_course: Course | None = None
        if course_query is not None:
            selected_course = _find_course(courses, course_query)

        items_by_id = {item.id: item for item in data.items}
        courses_by_id = {course.id: course for course in courses}
        results = [
            OpenTask(
                task=task,
                item=items_by_id[task.curriculum_item_id],
                course=courses_by_id[items_by_id[task.curriculum_item_id].course_id],
            )
            for task in data.tasks
            if task.completed_at is None
            and (
                selected_course is None
                or items_by_id[task.curriculum_item_id].course_id
                == selected_course.id
            )
        ]
        return sorted(
            results,
            key=lambda result: (
                _curriculum_order_key(
                    result.item,
                    items_by_id,
                    courses_by_id,
                ),
                _task_priority_key(result.task),
            ),
        )

    def progress_summary(self) -> list[CourseProgressSummary]:
        data = self._load_data()
        progress_by_item = {
            progress.curriculum_item_id: progress for progress in data.progress
        }
        summaries: list[CourseProgressSummary] = []
        for course in sorted(
            data.courses,
            key=lambda candidate: (
                candidate.title.casefold(),
                candidate.code.casefold(),
            ),
        ):
            items = [item for item in data.items if item.course_id == course.id]
            item_ids = {item.id for item in items}
            tasks = [
                task for task in data.tasks if task.curriculum_item_id in item_ids
            ]
            sessions = [
                session
                for session in data.sessions
                if session.curriculum_item_id in item_ids
            ]
            statuses = [
                (
                    progress_by_item[item.id].status.code
                    if item.id in progress_by_item
                    else StudyProgressStatus.NOT_STARTED
                )
                for item in items
            ]
            summaries.append(
                CourseProgressSummary(
                    course=course,
                    total_items=len(items),
                    not_started_items=statuses.count(
                        StudyProgressStatus.NOT_STARTED
                    ),
                    in_progress_items=statuses.count(
                        StudyProgressStatus.IN_PROGRESS
                    ),
                    mastered_items=statuses.count(StudyProgressStatus.MASTERED),
                    open_tasks=sum(task.completed_at is None for task in tasks),
                    completed_tasks=sum(
                        task.completed_at is not None for task in tasks
                    ),
                    total_study_minutes=sum(
                        _session_duration_minutes(session)
                        for session in sessions
                    ),
                )
            )
        return summaries

    def _resume_from_data(self, data: _StudyData) -> ResumeLearning | None:
        latest_session = max(
            (session for session in data.sessions if session.ended_at is not None),
            key=lambda session: session.ended_at,
            default=None,
        )
        latest_progress = None
        if latest_session is None:
            latest_progress = max(
                data.progress,
                key=lambda progress: progress.status_updated_at,
                default=None,
            )
        item_id = (
            latest_session.curriculum_item_id
            if latest_session is not None
            else (
                latest_progress.curriculum_item_id
                if latest_progress is not None
                else None
            )
        )
        if item_id is None:
            return None

        item = _item_by_id(data.items, item_id)
        course = _course_by_id(data.courses, item.course_id)
        item_progress = next(
            (
                progress
                for progress in data.progress
                if progress.curriculum_item_id == item.id
            ),
            None,
        )
        open_tasks = tuple(
            sorted(
                (
                    task
                    for task in data.tasks
                    if task.curriculum_item_id == item.id
                    and task.completed_at is None
                ),
                key=_task_priority_key,
            )
        )
        if latest_session is not None:
            assert latest_session.ended_at is not None
            activity_at = latest_session.ended_at
            duration = _session_duration_minutes(latest_session)
        else:
            assert latest_progress is not None
            activity_at = latest_progress.status_updated_at
            duration = None
        return ResumeLearning(
            item=item,
            course=course,
            last_activity_at=activity_at,
            last_session_duration_minutes=duration,
            progress_status=(
                item_progress.status
                if item_progress is not None
                else StudyProgressStatus(StudyProgressStatus.NOT_STARTED)
            ),
            open_tasks=open_tasks,
        )

    def _load_data(self) -> _StudyData:
        with self._unit_of_work_factory() as unit_of_work:
            return _StudyData(
                courses=tuple(unit_of_work.courses.list_all()),
                items=tuple(unit_of_work.curriculum_items.list_all()),
                tasks=tuple(unit_of_work.study_tasks.list_all()),
                sessions=tuple(unit_of_work.study_sessions.list_all()),
                progress=tuple(unit_of_work.study_progress.list_all()),
            )


def _task_priority_key(task: StudyTask) -> tuple[int, str, str]:
    return (
        TASK_TYPE_PRIORITY.get(task.task_type.code, len(TASK_TYPE_PRIORITY)),
        task.title.casefold(),
        str(task.id),
    )


def _curriculum_order_key(
    item: CurriculumItem,
    items_by_id: dict[UUID, CurriculumItem],
    courses_by_id: dict[UUID, Course],
) -> tuple[tuple[str, str], tuple[tuple[int, str], ...]]:
    course = courses_by_id[item.course_id]
    path: list[tuple[int, str]] = []
    current = item
    visited: set[UUID] = set()
    while True:
        if current.id in visited:
            break
        visited.add(current.id)
        path.append((current.order, current.code.casefold()))
        if current.parent_id is None or current.parent_id not in items_by_id:
            break
        current = items_by_id[current.parent_id]
    path.reverse()
    return (
        (course.title.casefold(), course.code.casefold()),
        tuple(path),
    )


def _session_duration_minutes(session: StudySession) -> int:
    if session.ended_at is None:
        return 0
    return max(
        0,
        round((session.ended_at - session.started_at).total_seconds() / 60),
    )


def _item_by_id(
    items: tuple[CurriculumItem, ...],
    item_id: UUID,
) -> CurriculumItem:
    item = next((candidate for candidate in items if candidate.id == item_id), None)
    if item is None:
        raise ValueError(f"Curriculum item '{item_id}' was not found")
    return item


def _course_by_id(courses: tuple[Course, ...], course_id: UUID) -> Course:
    course = next(
        (candidate for candidate in courses if candidate.id == course_id),
        None,
    )
    if course is None:
        raise ValueError(f"Course '{course_id}' was not found")
    return course


def _find_course(courses: tuple[Course, ...], query: str) -> Course:
    normalized_query = query.casefold()
    matches = [
        course
        for course in courses
        if course.code.casefold() == normalized_query
        or course.title.casefold() == normalized_query
    ]
    if not matches:
        raise ValueError(f"Course '{query}' was not found")
    if len(matches) > 1:
        raise ValueError(f"Course '{query}' is ambiguous")
    return matches[0]
