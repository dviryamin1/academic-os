from collections.abc import Iterator
from datetime import datetime
from uuid import uuid4

import pytest

from academic_os.application.services import StudyWorkflowService
from academic_os.domain import (
    Course,
    CurriculumItem,
    CurriculumItemType,
    Institution,
    StudyProgress,
    StudyProgressStatus,
    StudySession,
    StudyTask,
    StudyTaskType,
)
from academic_os.infrastructure.persistence.sqlalchemy.database import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from academic_os.infrastructure.persistence.sqlalchemy.models import Base
from academic_os.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@pytest.fixture
def session_factory(tmp_path) -> Iterator[SessionFactory]:
    database_path = tmp_path / "study-workflow-test.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def test_resume_returns_none_without_sessions_or_progress(
    session_factory: SessionFactory,
) -> None:
    service = _service(session_factory)
    _seed_curriculum(session_factory)

    assert service.resume_learning() is None


def test_resume_uses_latest_session_and_includes_item_context(
    session_factory: SessionFactory,
) -> None:
    first, second, _ = _seed_curriculum(session_factory)
    open_task = _task(second, StudyTaskType.READING)
    completed_task = _task(
        second,
        StudyTaskType.SUMMARY,
        completed_at=datetime(2026, 11, 12, 11, 0),
    )
    progress = _progress(
        second,
        StudyProgressStatus.IN_PROGRESS,
        datetime(2026, 11, 10, 9, 0),
    )
    sessions = (
        _session(first, datetime(2026, 11, 11, 10, 0), 20),
        _session(second, datetime(2026, 11, 12, 10, 0), 45),
    )
    _add_activity(
        session_factory,
        tasks=(open_task, completed_task),
        progress=(progress,),
        sessions=sessions,
    )

    resume = _service(session_factory).resume_learning()

    assert resume is not None
    assert resume.item == second
    assert resume.course.title == "Course A"
    assert resume.last_activity_at == datetime(2026, 11, 12, 10, 45)
    assert resume.last_session_duration_minutes == 45
    assert resume.progress_status.code == StudyProgressStatus.IN_PROGRESS
    assert resume.open_tasks == (open_task,)


def test_resume_falls_back_to_latest_progress_timestamp(
    session_factory: SessionFactory,
) -> None:
    first, second, _ = _seed_curriculum(session_factory)
    _add_activity(
        session_factory,
        progress=(
            _progress(
                second,
                StudyProgressStatus.IN_PROGRESS,
                datetime(2026, 11, 12, 10, 0),
            ),
            _progress(
                first,
                StudyProgressStatus.MASTERED,
                datetime(2026, 11, 13, 10, 0),
            ),
        ),
    )

    resume = _service(session_factory).resume_learning()

    assert resume is not None
    assert resume.item == first
    assert resume.last_activity_at == datetime(2026, 11, 13, 10, 0)
    assert resume.last_session_duration_minutes is None


def test_recommendation_prefers_resume_item_and_task_type_priority(
    session_factory: SessionFactory,
) -> None:
    first, second, third = _seed_curriculum(session_factory)
    reading = _task(second, StudyTaskType.READING)
    summary = _task(second, StudyTaskType.SUMMARY)
    completed = _task(
        second,
        StudyTaskType.READING,
        title="Already read",
        completed_at=datetime(2026, 11, 12, 12, 0),
    )
    earlier_item_task = _task(first, StudyTaskType.READING)
    _add_activity(
        session_factory,
        tasks=(summary, reading, completed, earlier_item_task),
        sessions=(_session(second, datetime(2026, 11, 12, 10, 0), 30),),
    )

    recommendation = _service(session_factory).recommend_next()

    assert recommendation is not None
    assert recommendation.task == reading
    assert recommendation.item == second
    assert recommendation.item != third
    assert recommendation.reason == (
        "Continue the item you studied most recently."
    )


def test_recommendation_uses_earliest_item_before_task_type(
    session_factory: SessionFactory,
) -> None:
    first, second, _ = _seed_curriculum(session_factory)
    early_summary = _task(first, StudyTaskType.SUMMARY)
    later_reading = _task(second, StudyTaskType.READING)
    _add_activity(session_factory, tasks=(later_reading, early_summary))

    recommendation = _service(session_factory).recommend_next()

    assert recommendation is not None
    assert recommendation.task == early_summary
    assert "earliest open summary task" in recommendation.reason


def test_open_tasks_exclude_completed_and_support_course_filter(
    session_factory: SessionFactory,
) -> None:
    first, _, third = _seed_curriculum(session_factory)
    open_a = _task(first, StudyTaskType.READING)
    open_b = _task(third, StudyTaskType.PRACTICE)
    completed = _task(
        first,
        StudyTaskType.REVIEW,
        completed_at=datetime(2026, 11, 12, 12, 0),
    )
    _add_activity(session_factory, tasks=(completed, open_b, open_a))
    service = _service(session_factory)

    assert [result.task for result in service.list_open_tasks()] == [
        open_a,
        open_b,
    ]
    assert [
        result.task
        for result in service.list_open_tasks("COURSE-B")
    ] == [open_b]
    assert [
        result.task
        for result in service.list_open_tasks("Course A")
    ] == [open_a]


def test_progress_summary_counts_status_tasks_and_minutes(
    session_factory: SessionFactory,
) -> None:
    first, second, third = _seed_curriculum(session_factory)
    _add_activity(
        session_factory,
        tasks=(
            _task(first, StudyTaskType.READING),
            _task(
                second,
                StudyTaskType.SUMMARY,
                completed_at=datetime(2026, 11, 12, 12, 0),
            ),
            _task(third, StudyTaskType.PRACTICE),
        ),
        progress=(
            _progress(
                first,
                StudyProgressStatus.IN_PROGRESS,
                datetime(2026, 11, 12, 10, 0),
            ),
            _progress(
                second,
                StudyProgressStatus.MASTERED,
                datetime(2026, 11, 13, 10, 0),
            ),
        ),
        sessions=(
            _session(first, datetime(2026, 11, 12, 10, 0), 30),
            _session(second, datetime(2026, 11, 13, 10, 0), 45),
            _session(third, datetime(2026, 11, 14, 10, 0), 20),
        ),
    )

    summaries = _service(session_factory).progress_summary()
    course_a, course_b = summaries

    assert course_a.course.title == "Course A"
    assert (
        course_a.total_items,
        course_a.not_started_items,
        course_a.in_progress_items,
        course_a.mastered_items,
    ) == (2, 0, 1, 1)
    assert (course_a.open_tasks, course_a.completed_tasks) == (1, 1)
    assert course_a.total_study_minutes == 75
    assert course_b.course.title == "Course B"
    assert course_b.not_started_items == 1
    assert course_b.open_tasks == 1
    assert course_b.total_study_minutes == 20


def _service(session_factory: SessionFactory) -> StudyWorkflowService:
    return StudyWorkflowService(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    )


def _seed_curriculum(
    session_factory: SessionFactory,
) -> tuple[CurriculumItem, CurriculumItem, CurriculumItem]:
    institution = Institution(id=uuid4(), name="University")
    course_a = Course(
        id=uuid4(),
        institution_id=institution.id,
        code="COURSE-A",
        title="Course A",
    )
    course_b = Course(
        id=uuid4(),
        institution_id=institution.id,
        code="COURSE-B",
        title="Course B",
    )
    first = _item(course_a, "A-01", order=1)
    second = _item(course_a, "A-02", order=2)
    third = _item(course_b, "B-01", order=1)
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.institutions.add(institution)
        unit_of_work.courses.add(course_a)
        unit_of_work.courses.add(course_b)
        unit_of_work.curriculum_items.add(first)
        unit_of_work.curriculum_items.add(second)
        unit_of_work.curriculum_items.add(third)
        unit_of_work.commit()
    return first, second, third


def _item(course: Course, code: str, *, order: int) -> CurriculumItem:
    return CurriculumItem(
        id=uuid4(),
        code=code,
        parent_id=None,
        title=f"Item {code}",
        item_type=CurriculumItemType(CurriculumItemType.TOPIC),
        course_id=course.id,
        source=None,
        pages=f"{order}-{order + 1}",
        order=order,
    )


def _task(
    item: CurriculumItem,
    task_type: str,
    *,
    title: str | None = None,
    completed_at: datetime | None = None,
) -> StudyTask:
    return StudyTask(
        id=uuid4(),
        curriculum_item_id=item.id,
        task_type=StudyTaskType(task_type),
        title=title or task_type.title(),
        due_at=None,
        completed_at=completed_at,
    )


def _progress(
    item: CurriculumItem,
    status: str,
    status_updated_at: datetime,
) -> StudyProgress:
    return StudyProgress(
        id=uuid4(),
        curriculum_item_id=item.id,
        status=StudyProgressStatus(status),
        status_updated_at=status_updated_at,
    )


def _session(
    item: CurriculumItem,
    started_at: datetime,
    minutes: int,
) -> StudySession:
    from datetime import timedelta

    return StudySession(
        id=uuid4(),
        curriculum_item_id=item.id,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=minutes),
    )


def _add_activity(
    session_factory: SessionFactory,
    *,
    tasks: tuple[StudyTask, ...] = (),
    progress: tuple[StudyProgress, ...] = (),
    sessions: tuple[StudySession, ...] = (),
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        for task in tasks:
            unit_of_work.study_tasks.add(task)
        for item_progress in progress:
            unit_of_work.study_progress.add(item_progress)
        for session in sessions:
            unit_of_work.study_sessions.add(session)
        unit_of_work.commit()
