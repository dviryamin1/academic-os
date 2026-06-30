import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from academic_os.application.services import (
    CourseProgressSummary,
    NextStudyRecommendation,
    ResumeLearning,
)
from academic_os.domain import (
    Course,
    CurriculumItem,
    CurriculumItemType,
    StudyProgressStatus,
    StudyTask,
    StudyTaskType,
)
from academic_os.interfaces.streamlit.navigation import (
    filter_navigation_entries,
    flatten_hierarchy,
    preserved_item_code,
)
from academic_os.interfaces.streamlit.rtl import (
    LEFT_TO_RIGHT_ISOLATE,
    POP_DIRECTIONAL_ISOLATE,
    isolated_code,
    isolated_title,
    local_item_code,
)
from academic_os.interfaces.streamlit.view_models import (
    OUTDATED_SCHEMA_MESSAGE,
    recommendation_card,
    resume_card,
    schema_error_message,
)
from academic_os.interfaces.streamlit_app import (
    _progress_summary_rows,
    _session_duration_minutes,
)
from academic_os.interfaces.streamlit_bootstrap import build_workspace_service


def test_session_duration_minutes_handles_completed_and_open_sessions() -> None:
    started_at = datetime(2026, 11, 15, 11, 30)

    assert (
        _session_duration_minutes(
            started_at,
            datetime(2026, 11, 15, 12, 0),
        )
        == 30
    )
    assert _session_duration_minutes(started_at, None) == 0


def test_hierarchy_flattening_preserves_depth_and_order() -> None:
    course_id = uuid4()
    chapter = _item("STAT-10", course_id=course_id, order=1)
    child = _item(
        "STAT-10.11",
        course_id=course_id,
        parent_id=chapter.id,
        order=2,
    )
    grandchild = _item(
        "STAT-10.11.1",
        course_id=course_id,
        parent_id=child.id,
        order=1,
    )
    article = _item("STAT-A01", course_id=course_id, order=2)

    entries = flatten_hierarchy([grandchild, article, child, chapter])

    assert [entry.item for entry in entries] == [
        chapter,
        child,
        grandchild,
        article,
    ]
    assert [entry.depth for entry in entries] == [0, 1, 2, 0]


def test_search_filters_code_hebrew_title_and_pages() -> None:
    course_id = uuid4()
    chapter = _item(
        "STAT-10",
        course_id=course_id,
        title="עקרונות של אמידה",
        pages="150-170",
    )
    child = _item(
        "STAT-10.8",
        course_id=course_id,
        parent_id=chapter.id,
        title="בדיקת השערות",
        pages="171-180",
    )
    entries = flatten_hierarchy([chapter, child])

    assert [entry.item for entry in filter_navigation_entries(
        entries, "10.8"
    )] == [child]
    assert [entry.item for entry in filter_navigation_entries(
        entries, "השערות"
    )] == [child]
    assert [entry.item for entry in filter_navigation_entries(
        entries, "150"
    )] == [chapter]


def test_selected_item_is_preserved_when_still_available() -> None:
    course_id = uuid4()
    first = _item("STAT-10", course_id=course_id, order=1)
    second = _item("STAT-11", course_id=course_id, order=2)
    entries = flatten_hierarchy([second, first])

    assert preserved_item_code(entries, "STAT-11") == "STAT-11"
    assert preserved_item_code(entries, "MISSING") == "STAT-10"
    assert preserved_item_code((), "STAT-11") is None


def test_rtl_helpers_preserve_titles_and_isolate_codes() -> None:
    title = "בדיקת השערות"

    assert local_item_code("STAT-10.11") == "10.11"
    assert local_item_code("DP-06.03") == "06.03"
    assert isolated_code("STAT-10.11") == (
        f"{LEFT_TO_RIGHT_ISOLATE}STAT-10.11{POP_DIRECTIONAL_ISOLATE}"
    )
    assert title in isolated_title(title)


def test_daily_card_projections_receive_complete_workflow_data() -> None:
    course = Course(
        id=uuid4(),
        institution_id=uuid4(),
        code="STAT",
        title="סטטיסטיקה ב'",
    )
    item = _item(
        "STAT-10.8",
        course_id=course.id,
        title="בדיקת השערות",
        pages="171-180",
    )
    task = StudyTask(
        id=uuid4(),
        curriculum_item_id=item.id,
        task_type=StudyTaskType(StudyTaskType.READING),
        title="Reading",
        due_at=None,
        completed_at=None,
    )
    resume = ResumeLearning(
        item=item,
        course=course,
        last_activity_at=datetime(2026, 11, 15, 12, 0),
        last_session_duration_minutes=30,
        progress_status=StudyProgressStatus(
            StudyProgressStatus.IN_PROGRESS
        ),
        open_tasks=(task,),
    )
    recommendation = NextStudyRecommendation(
        task=task,
        item=item,
        course=course,
        reason="Continue the item you studied most recently.",
    )

    assert resume_card(resume).session_minutes == 30
    assert resume_card(resume).item_title == "בדיקת השערות"
    assert recommendation_card(recommendation).task_title == "Reading"
    assert recommendation_card(recommendation).pages == "171-180"


def test_outdated_schema_error_has_friendly_message() -> None:
    error = OperationalError(
        "SELECT study_progress.status_updated_at",
        {},
        Exception("sqlite3.OperationalError: no such column"),
    )

    assert schema_error_message(error) == OUTDATED_SCHEMA_MESSAGE
    assert schema_error_message(ValueError("another error")) is None


def test_progress_summary_rows_are_ready_for_streamlit_table() -> None:
    course = Course(
        id=uuid4(),
        institution_id=uuid4(),
        code="STAT",
        title="סטטיסטיקה ב'",
    )
    summary = CourseProgressSummary(
        course=course,
        total_items=10,
        not_started_items=4,
        in_progress_items=3,
        mastered_items=3,
        open_tasks=5,
        completed_tasks=7,
        total_study_minutes=125,
    )

    assert _progress_summary_rows([summary])[0]["Study minutes"] == 125


def test_streamlit_app_starts_before_database_initialization(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "uninitialized.db"
    monkeypatch.setenv(
        "ACADEMIC_OS_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )

    app = AppTest.from_file(str(_app_path())).run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "Academic OS"
    assert "not initialized" in app.info[0].value


def test_streamlit_uses_sidebar_search_instead_of_child_dropdowns(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "hierarchy.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    source = tmp_path / "hierarchy.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "STAT-10",
                        "parent_id": None,
                        "type": "unit",
                        "course": "סטטיסטיקה ב'",
                        "source": "כרך א'",
                        "title": "עקרונות של אמידה",
                        "pages": "150-170",
                    },
                    {
                        "id": "STAT-10.11",
                        "parent_id": "STAT-10",
                        "type": "subtopic",
                        "course": "סטטיסטיקה ב'",
                        "source": "כרך א'",
                        "title": "בדיקת השערות",
                        "pages": "166",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = build_workspace_service(database_url)
    service.initialize_database()
    service.import_curriculum(
        source,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )
    monkeypatch.setenv("ACADEMIC_OS_DATABASE_URL", database_url)

    app = AppTest.from_file(str(_app_path())).run(timeout=10)

    assert not app.exception
    assert {selectbox.label for selectbox in app.selectbox} == {"Course"}
    assert any(field.label == "Search items" for field in app.text_input)
    assert all(
        selectbox.label not in {"Top-level item", "Child item"}
        for selectbox in app.selectbox
    )
    assert any(
        "עקרונות של אמידה" in markdown.value
        for markdown in app.markdown
    )

    search = next(
        field for field in app.text_input if field.label == "Search items"
    )
    search.input("STAT-10.11").run(timeout=10)
    child_button = next(
        button for button in app.button if "10.11" in button.label
    )
    child_button.click().run(timeout=10)

    assert not app.exception
    assert any(
        "בדיקת השערות" in markdown.value
        for markdown in app.markdown
    )


def test_streamlit_reports_and_upgrades_pre_sprint_3_database(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "pre-sprint-3.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    configuration = Config("alembic.ini")
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "0002")

    source = tmp_path / "curriculum.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "STAT-10",
                        "parent_id": None,
                        "type": "unit",
                        "course": "סטטיסטיקה ב'",
                        "source": "כרך א'",
                        "title": "עקרונות של אמידה",
                        "pages": "150-170",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = build_workspace_service(database_url)
    service.import_curriculum(
        source,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )
    monkeypatch.setenv("ACADEMIC_OS_DATABASE_URL", database_url)

    app = AppTest.from_file(str(_app_path())).run(timeout=10)

    assert not app.exception
    assert app.error[0].value == OUTDATED_SCHEMA_MESSAGE
    upgrade_button = next(
        button for button in app.button if button.label == "Upgrade"
    )
    upgrade_button.click().run(timeout=10)

    assert not app.exception
    assert not any(
        message.value == OUTDATED_SCHEMA_MESSAGE for message in app.error
    )
    assert any(
        "עקרונות של אמידה" in markdown.value
        for markdown in app.markdown
    )


def _app_path() -> Path:
    return (
        Path(__file__).parents[2]
        / "src"
        / "academic_os"
        / "interfaces"
        / "streamlit_app.py"
    )


def _item(
    code: str,
    *,
    course_id: UUID,
    parent_id: UUID | None = None,
    order: int = 0,
    title: str = "כותרת בעברית",
    pages: str | None = None,
) -> CurriculumItem:
    return CurriculumItem(
        id=uuid4(),
        code=code,
        parent_id=parent_id,
        title=title,
        item_type=CurriculumItemType(CurriculumItemType.TOPIC),
        course_id=course_id,
        source=None,
        pages=pages,
        order=order,
    )
