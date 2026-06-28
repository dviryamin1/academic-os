import json
from collections.abc import Iterator
from datetime import datetime

import pytest

from academic_os.application.services import WorkspaceService
from academic_os.domain import StudyProgressStatus
from academic_os.infrastructure.importers import JsonCurriculumImporter
from academic_os.infrastructure.persistence.sqlalchemy.database import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from academic_os.infrastructure.persistence.sqlalchemy.models import Base
from academic_os.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

FIXED_NOW = datetime(2026, 11, 15, 12, 0)


@pytest.fixture
def session_factory(tmp_path) -> Iterator[SessionFactory]:
    database_path = tmp_path / "workspace-test.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture
def curriculum_file(tmp_path):
    source = tmp_path / "curriculum.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "items": [
                    {
                        "id": "STAT-10",
                        "parent_id": None,
                        "level": 1,
                        "type": "unit",
                        "course": "סטטיסטיקה ב'",
                        "source": "יחידה 10",
                        "part": None,
                        "title": "אמידה",
                        "pages": "1-20",
                    },
                    {
                        "id": "STAT-10.8",
                        "parent_id": "STAT-10",
                        "level": 2,
                        "type": "subtopic",
                        "course": "סטטיסטיקה ב'",
                        "source": "יחידה 10",
                        "part": None,
                        "title": "בדיקת השערות",
                        "pages": "21-35",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return source


@pytest.fixture
def service(session_factory: SessionFactory) -> WorkspaceService:
    return WorkspaceService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        JsonCurriculumImporter(),
        clock=lambda: FIXED_NOW,
    )


def test_import_list_and_show_curriculum_item(
    service: WorkspaceService,
    session_factory: SessionFactory,
    curriculum_file,
) -> None:
    summary = service.import_curriculum(
        curriculum_file,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )

    assert summary.course_count == 1
    assert summary.curriculum_item_count == 2

    repeated_summary = service.import_curriculum(
        curriculum_file,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )
    assert repeated_summary == summary

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert len(unit_of_work.institutions.list_all()) == 1
        assert len(unit_of_work.degrees.list_all()) == 1
        assert len(unit_of_work.degree_courses.list_all()) == 1
        assert len(unit_of_work.curriculum_items.list_all()) == 2

    assert [course.title for course in service.list_courses()] == [
        "סטטיסטיקה ב'"
    ]
    assert [item.code for item in service.list_curriculum_items("STAT")] == [
        "STAT-10",
        "STAT-10.8",
    ]
    assert [
        item.code
        for item in service.list_curriculum_items("סטטיסטיקה ב'")
    ] == ["STAT-10", "STAT-10.8"]

    workspace = service.show_item("STAT-10.8")
    assert workspace.item.title == "בדיקת השערות"
    assert workspace.item.pages == "21-35"
    assert workspace.course.title == "סטטיסטיקה ב'"
    assert workspace.parent is not None
    assert workspace.parent.code == "STAT-10"

    parent_workspace = service.show_item("STAT-10")
    assert [child.code for child in parent_workspace.children] == ["STAT-10.8"]


def test_create_and_complete_default_tasks(
    service: WorkspaceService,
    curriculum_file,
) -> None:
    _import(service, curriculum_file)

    tasks = service.create_default_tasks("STAT-10.8")
    repeated_tasks = service.create_default_tasks("STAT-10.8")

    assert [task.task_type.code for task in tasks] == [
        "reading",
        "summary",
        "practice",
        "review",
    ]
    assert repeated_tasks == tasks

    completed = service.complete_task(tasks[0].id)
    assert completed.completed_at == FIXED_NOW
    loaded = service.show_item("STAT-10.8")
    loaded_task = next(task for task in loaded.tasks if task.id == completed.id)
    assert loaded_task.completed_at == FIXED_NOW


def test_note_session_and_progress_workflow(
    service: WorkspaceService,
    session_factory: SessionFactory,
    curriculum_file,
) -> None:
    _import(service, curriculum_file)

    note = service.add_note("STAT-10.8", "הערה בעברית")
    study_session = service.log_study_session("STAT-10.8", minutes=30)
    progress = service.set_progress(
        "STAT-10.8",
        StudyProgressStatus.IN_PROGRESS,
    )
    mastered = service.set_progress(
        "STAT-10.8",
        StudyProgressStatus.MASTERED,
    )

    assert note.content == "הערה בעברית"
    assert study_session.ended_at == FIXED_NOW
    assert study_session.started_at == datetime(2026, 11, 15, 11, 30)
    assert mastered.id == progress.id
    assert mastered.status.code == StudyProgressStatus.MASTERED

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.notes.get(note.id) == note
        assert (
            unit_of_work.study_sessions.get(study_session.id)
            == study_session
        )
        assert unit_of_work.study_progress.get(mastered.id) == mastered

    workspace = service.show_item("STAT-10.8")
    assert workspace.notes == (note,)
    assert workspace.study_sessions == (study_session,)
    assert workspace.progress == mastered


def test_database_initialization_uses_injected_operation(
    session_factory: SessionFactory,
) -> None:
    initialization_calls: list[str] = []
    service = WorkspaceService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        JsonCurriculumImporter(),
        database_initializer=lambda: initialization_calls.append("called"),
    )

    service.initialize_database()

    assert initialization_calls == ["called"]


def _import(service: WorkspaceService, curriculum_file) -> None:
    service.import_curriculum(
        curriculum_file,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )
