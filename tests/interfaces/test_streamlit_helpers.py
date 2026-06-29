import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from streamlit.testing.v1 import AppTest

from academic_os.application.services import CourseProgressSummary
from academic_os.domain import Course, CurriculumItem, CurriculumItemType
from academic_os.interfaces.streamlit_app import (
    FIRST_STRONG_ISOLATE,
    LEFT_TO_RIGHT_ISOLATE,
    POP_DIRECTIONAL_ISOLATE,
    _descendant_items,
    _local_item_code,
    _progress_summary_rows,
    _resolve_navigation_target,
    _safe_item_label,
    _session_duration_minutes,
    _top_level_items,
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


def test_top_level_items_are_separate_from_children() -> None:
    course_id = uuid4()
    chapter = _item("STAT-10", course_id=course_id, order=1)
    child = _item(
        "STAT-10.11",
        course_id=course_id,
        parent_id=chapter.id,
        order=1,
    )
    article = _item("STAT-A01", course_id=course_id, order=2)
    items = [child, article, chapter]

    assert _top_level_items(items) == (chapter, article)
    assert _descendant_items(items, chapter.id) == (child,)


def test_navigation_target_opens_parent_or_selected_child() -> None:
    course_id = uuid4()
    parent = _item("DP-06", course_id=course_id)
    child = _item(
        "DP-06.03",
        course_id=course_id,
        parent_id=parent.id,
    )
    items = [parent, child]

    assert _resolve_navigation_target(items, parent.code) == (parent, None)
    assert _resolve_navigation_target(items, child.code) == (parent, child)


def test_local_codes_and_bidi_labels_preserve_internal_values() -> None:
    item = _item(
        "STAT-10.11",
        course_id=uuid4(),
        title="בדיקת השערות",
    )

    assert _local_item_code(item.code) == "10.11"
    assert _local_item_code("DP-06.03") == "06.03"
    assert item.code == "STAT-10.11"

    label = _safe_item_label(item)
    assert item.title in label
    assert (
        f"{LEFT_TO_RIGHT_ISOLATE}{item.code}{POP_DIRECTIONAL_ISOLATE}"
        in label
    )
    assert (
        f"{FIRST_STRONG_ISOLATE}{item.title}{POP_DIRECTIONAL_ISOLATE}"
        in label
    )


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

    assert _progress_summary_rows([summary]) == [
        {
            "Course": "סטטיסטיקה ב'",
            "Items": 10,
            "Not started": 4,
            "In progress": 3,
            "Mastered": 3,
            "Open tasks": 5,
            "Completed tasks": 7,
            "Study minutes": 125,
        }
    ]


def test_streamlit_app_starts_before_database_initialization(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "uninitialized.db"
    monkeypatch.setenv(
        "ACADEMIC_OS_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    app_path = (
        Path(__file__).parents[2]
        / "src"
        / "academic_os"
        / "interfaces"
        / "streamlit_app.py"
    )

    app = AppTest.from_file(str(app_path)).run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "Academic OS"
    assert "Initialize the database" in app.info[0].value


def test_streamlit_hierarchy_selects_child_workspace(
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
                    {
                        "id": "STAT-A01",
                        "parent_id": None,
                        "type": "article",
                        "course": "סטטיסטיקה ב'",
                        "source": "מקראה",
                        "title": "מאמר לדוגמה",
                        "pages": "1-10",
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
    child = service.show_item("STAT-10.11").item
    monkeypatch.setenv("ACADEMIC_OS_DATABASE_URL", database_url)
    app_path = (
        Path(__file__).parents[2]
        / "src"
        / "academic_os"
        / "interfaces"
        / "streamlit_app.py"
    )

    app = AppTest.from_file(str(app_path)).run(timeout=10)

    assert not app.exception
    selectboxes = {selectbox.label: selectbox for selectbox in app.selectbox}
    assert set(selectboxes) == {"Course", "Top-level item", "Child item"}
    assert len(selectboxes["Top-level item"].options) == 2
    assert all(
        "STAT-10.11" not in option
        for option in selectboxes["Top-level item"].options
    )
    assert any(
        "10.11" in option
        for option in selectboxes["Child item"].options
    )
    assert all(
        "STAT-10.11" not in option
        for option in selectboxes["Child item"].options
    )

    selectboxes["Child item"].select(str(child.id)).run(timeout=10)

    assert not app.exception
    assert any(
        "בדיקת השערות" in markdown.value
        for markdown in app.markdown
    )


def _item(
    code: str,
    *,
    course_id: UUID,
    parent_id: UUID | None = None,
    order: int = 0,
    title: str = "כותרת בעברית",
) -> CurriculumItem:
    return CurriculumItem(
        id=uuid4(),
        code=code,
        parent_id=parent_id,
        title=title,
        item_type=CurriculumItemType(CurriculumItemType.TOPIC),
        course_id=course_id,
        source=None,
        pages=None,
        order=order,
    )
