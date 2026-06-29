from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeVar
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from academic_os.application.ports import (
    CurriculumImporter,
    Repository,
    UnitOfWork,
)
from academic_os.domain import (
    Course,
    CurriculumItem,
    DegreeCourse,
    Note,
    StudyProgress,
    StudyProgressStatus,
    StudySession,
    StudyTask,
    StudyTaskType,
)

WORKSPACE_NAMESPACE = uuid5(NAMESPACE_URL, "academic-os:workspace:v1")
VALID_PROGRESS_STATUSES = frozenset(
    {
        StudyProgressStatus.NOT_STARTED,
        StudyProgressStatus.IN_PROGRESS,
        StudyProgressStatus.MASTERED,
    }
)
DEFAULT_TASK_DEFINITIONS = (
    (StudyTaskType.READING, "Reading"),
    (StudyTaskType.SUMMARY, "Summary"),
    (StudyTaskType.PRACTICE, "Practice"),
    (StudyTaskType.REVIEW, "Review"),
)
TASK_ORDER = {
    task_type: position
    for position, (task_type, _) in enumerate(DEFAULT_TASK_DEFINITIONS)
}

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]
DatabaseInitializer = Callable[[], None]
EntityT = TypeVar("EntityT")


class WorkspaceError(ValueError):
    """The requested workspace operation cannot be completed."""


@dataclass(frozen=True, slots=True)
class ImportSummary:
    institution_name: str
    degree_name: str
    course_count: int
    curriculum_item_count: int


@dataclass(frozen=True, slots=True)
class ItemWorkspace:
    item: CurriculumItem
    course: Course
    parent: CurriculumItem | None
    children: tuple[CurriculumItem, ...]
    tasks: tuple[StudyTask, ...]
    notes: tuple[Note, ...]
    study_sessions: tuple[StudySession, ...]
    progress: StudyProgress | None


class WorkspaceService:
    """Coordinates the first curriculum-item study workflow."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        curriculum_importer: CurriculumImporter[Path],
        *,
        clock: Clock = datetime.now,
        database_initializer: DatabaseInitializer | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._curriculum_importer = curriculum_importer
        self._clock = clock
        self._database_initializer = database_initializer

    def initialize_database(self) -> None:
        if self._database_initializer is None:
            raise WorkspaceError("Database initialization is not configured")
        self._database_initializer()

    def import_curriculum(
        self,
        source: Path,
        *,
        institution_name: str,
        degree_name: str,
    ) -> ImportSummary:
        result = self._curriculum_importer.import_curriculum(
            source,
            institution_name=institution_name,
            degree_name=degree_name,
        )

        with self._unit_of_work_factory() as unit_of_work:
            _upsert(
                unit_of_work.institutions,
                result.institution.id,
                result.institution,
            )
            _upsert(
                unit_of_work.degrees,
                result.degree.id,
                result.degree,
            )
            for course in result.courses:
                _upsert(unit_of_work.courses, course.id, course)
                degree_course = DegreeCourse(
                    id=_stable_uuid(
                        "degree-course",
                        str(result.degree.id),
                        str(course.id),
                    ),
                    degree_id=result.degree.id,
                    course_id=course.id,
                    credits=None,
                )
                _upsert(
                    unit_of_work.degree_courses,
                    degree_course.id,
                    degree_course,
                )
            for item in result.curriculum_items:
                _upsert(unit_of_work.curriculum_items, item.id, item)
            unit_of_work.commit()

        return ImportSummary(
            institution_name=result.institution.name,
            degree_name=result.degree.name,
            course_count=len(result.courses),
            curriculum_item_count=len(result.curriculum_items),
        )

    def list_courses(self) -> list[Course]:
        with self._unit_of_work_factory() as unit_of_work:
            courses = unit_of_work.courses.list_all()
        return sorted(courses, key=lambda course: course.title.casefold())

    def list_curriculum_items(self, course_query: str) -> list[CurriculumItem]:
        with self._unit_of_work_factory() as unit_of_work:
            course = _find_course(unit_of_work.courses.list_all(), course_query)
            items = [
                item
                for item in unit_of_work.curriculum_items.list_all()
                if item.course_id == course.id
            ]
        return sorted(items, key=lambda item: (item.order, item.code.casefold()))

    def show_item(self, item_code: str) -> ItemWorkspace:
        with self._unit_of_work_factory() as unit_of_work:
            items = unit_of_work.curriculum_items.list_all()
            item = _find_item(items, item_code)
            course = unit_of_work.courses.get(item.course_id)
            if course is None:
                raise WorkspaceError(
                    f"Course for curriculum item '{item.code}' was not found"
                )

            parent = None
            if item.parent_id is not None:
                parent = next(
                    (
                        candidate
                        for candidate in items
                        if candidate.id == item.parent_id
                    ),
                    None,
                )
            children = tuple(
                sorted(
                    (
                        candidate
                        for candidate in items
                        if candidate.parent_id == item.id
                    ),
                    key=lambda candidate: (
                        candidate.order,
                        candidate.code.casefold(),
                    ),
                )
            )
            tasks = tuple(
                sorted(
                    (
                        task
                        for task in unit_of_work.study_tasks.list_all()
                        if task.curriculum_item_id == item.id
                    ),
                    key=lambda task: TASK_ORDER.get(
                        task.task_type.code,
                        len(TASK_ORDER),
                    ),
                )
            )
            notes = tuple(
                sorted(
                    (
                        note
                        for note in unit_of_work.notes.list_all()
                        if note.curriculum_item_id == item.id
                    ),
                    key=lambda note: note.created_at,
                    reverse=True,
                )
            )
            study_sessions = tuple(
                sorted(
                    (
                        session
                        for session in unit_of_work.study_sessions.list_all()
                        if session.curriculum_item_id == item.id
                    ),
                    key=lambda session: session.started_at,
                    reverse=True,
                )
            )
            progress = next(
                (
                    candidate
                    for candidate in unit_of_work.study_progress.list_all()
                    if candidate.curriculum_item_id == item.id
                ),
                None,
            )

        return ItemWorkspace(
            item=item,
            course=course,
            parent=parent,
            children=children,
            tasks=tasks,
            notes=notes,
            study_sessions=study_sessions,
            progress=progress,
        )

    def create_default_tasks(self, item_code: str) -> list[StudyTask]:
        with self._unit_of_work_factory() as unit_of_work:
            item = _find_item(
                unit_of_work.curriculum_items.list_all(),
                item_code,
            )
            existing_tasks = {
                task.task_type.code: task
                for task in unit_of_work.study_tasks.list_all()
                if task.curriculum_item_id == item.id
            }
            tasks: list[StudyTask] = []
            for task_type, title in DEFAULT_TASK_DEFINITIONS:
                task = existing_tasks.get(task_type)
                if task is None:
                    task = StudyTask(
                        id=_stable_uuid(
                            "default-task",
                            str(item.id),
                            task_type,
                        ),
                        curriculum_item_id=item.id,
                        task_type=StudyTaskType(task_type),
                        title=title,
                        due_at=None,
                        completed_at=None,
                    )
                    unit_of_work.study_tasks.add(task)
                tasks.append(task)
            unit_of_work.commit()
        return tasks

    def complete_task(self, task_id: UUID) -> StudyTask:
        with self._unit_of_work_factory() as unit_of_work:
            task = unit_of_work.study_tasks.get(task_id)
            if task is None:
                raise WorkspaceError(f"Study task '{task_id}' was not found")
            completed_task = replace(task, completed_at=self._clock())
            unit_of_work.study_tasks.update(completed_task)
            unit_of_work.commit()
        return completed_task

    def add_note(self, item_code: str, content: str) -> Note:
        if not content.strip():
            raise WorkspaceError("Note content cannot be empty")

        with self._unit_of_work_factory() as unit_of_work:
            item = _find_item(
                unit_of_work.curriculum_items.list_all(),
                item_code,
            )
            note = Note(
                id=uuid4(),
                curriculum_item_id=item.id,
                content=content,
                created_at=self._clock(),
            )
            unit_of_work.notes.add(note)
            unit_of_work.commit()
        return note

    def log_study_session(
        self,
        item_code: str,
        *,
        minutes: int,
    ) -> StudySession:
        if minutes <= 0:
            raise WorkspaceError("Session minutes must be greater than zero")

        with self._unit_of_work_factory() as unit_of_work:
            item = _find_item(
                unit_of_work.curriculum_items.list_all(),
                item_code,
            )
            ended_at = self._clock()
            study_session = StudySession(
                id=uuid4(),
                curriculum_item_id=item.id,
                started_at=ended_at - timedelta(minutes=minutes),
                ended_at=ended_at,
            )
            unit_of_work.study_sessions.add(study_session)
            unit_of_work.commit()
        return study_session

    def set_progress(
        self,
        item_code: str,
        status: str,
    ) -> StudyProgress:
        if status not in VALID_PROGRESS_STATUSES:
            allowed = ", ".join(sorted(VALID_PROGRESS_STATUSES))
            raise WorkspaceError(
                f"Unknown progress status '{status}'. Use one of: {allowed}"
            )

        with self._unit_of_work_factory() as unit_of_work:
            item = _find_item(
                unit_of_work.curriculum_items.list_all(),
                item_code,
            )
            progress = next(
                (
                    candidate
                    for candidate in unit_of_work.study_progress.list_all()
                    if candidate.curriculum_item_id == item.id
                ),
                None,
            )
            if progress is None:
                progress = StudyProgress(
                    id=_stable_uuid("study-progress", str(item.id)),
                    curriculum_item_id=item.id,
                    status=StudyProgressStatus(status),
                    status_updated_at=self._clock(),
                )
                unit_of_work.study_progress.add(progress)
            else:
                progress = replace(
                    progress,
                    status=StudyProgressStatus(status),
                    status_updated_at=self._clock(),
                )
                unit_of_work.study_progress.update(progress)
            unit_of_work.commit()
        return progress


def _find_course(courses: list[Course], query: str) -> Course:
    normalized_query = query.casefold()
    matches = [
        course
        for course in courses
        if course.code.casefold() == normalized_query
        or course.title.casefold() == normalized_query
    ]
    if not matches:
        raise WorkspaceError(f"Course '{query}' was not found")
    if len(matches) > 1:
        raise WorkspaceError(f"Course '{query}' is ambiguous")
    return matches[0]


def _find_item(items: list[CurriculumItem], code: str) -> CurriculumItem:
    normalized_code = code.casefold()
    matches = [item for item in items if item.code.casefold() == normalized_code]
    if not matches:
        raise WorkspaceError(f"Curriculum item '{code}' was not found")
    if len(matches) > 1:
        raise WorkspaceError(
            f"Curriculum item code '{code}' exists in more than one course"
        )
    return matches[0]


def _upsert(
    repository: Repository[EntityT],
    entity_id: UUID,
    entity: EntityT,
) -> None:
    if repository.get(entity_id) is None:
        repository.add(entity)
    else:
        repository.update(entity)


def _stable_uuid(kind: str, *parts: str) -> UUID:
    return uuid5(WORKSPACE_NAMESPACE, ":".join((kind, *parts)))
