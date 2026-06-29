from html import escape
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import UUID

import streamlit as st
from sqlalchemy.exc import OperationalError

from academic_os.application.services import (
    ItemWorkspace,
    WorkspaceError,
    WorkspaceService,
)
from academic_os.domain import StudyProgressStatus
from academic_os.domain import CurriculumItem
from academic_os.interfaces.streamlit_bootstrap import (
    build_workspace_service,
    default_database_url,
)

DEFAULT_INSTITUTION_NAME = "האוניברסיטה הפתוחה"
DEFAULT_DEGREE_NAME = "פסיכולוגיה"
PROGRESS_STATUSES = (
    StudyProgressStatus.NOT_STARTED,
    StudyProgressStatus.IN_PROGRESS,
    StudyProgressStatus.MASTERED,
)
LEFT_TO_RIGHT_ISOLATE = "\u2066"
FIRST_STRONG_ISOLATE = "\u2068"
POP_DIRECTIONAL_ISOLATE = "\u2069"


@st.cache_resource
def _build_service(database_url: str) -> WorkspaceService:
    return build_workspace_service(database_url)


def run() -> None:
    st.set_page_config(
        page_title="Academic OS",
        page_icon="📚",
        layout="wide",
    )
    _apply_workspace_style()

    st.title("Academic OS")
    st.caption("A focused workspace for one curriculum item at a time.")

    database_url, service = _render_setup_sidebar()
    _render_flash_message()

    try:
        courses = service.list_courses()
    except OperationalError:
        st.info(
            "Initialize the database from the sidebar, then import a "
            "curriculum JSON file."
        )
        return

    if not courses:
        st.info(
            "No curriculum is available yet. Import a JSON file from the "
            "sidebar to begin."
        )
        return

    st.subheader("Choose what to study")
    courses_by_id = {str(course.id): course for course in courses}
    course_ids = list(courses_by_id)
    if st.session_state.get("navigation-course-id") not in course_ids:
        st.session_state["navigation-course-id"] = course_ids[0]
    selected_course_id = st.selectbox(
        "Course",
        options=course_ids,
        format_func=lambda course_id: courses_by_id[course_id].title,
        key="navigation-course-id",
    )
    selected_course = courses_by_id[selected_course_id]
    if st.session_state.get("_active-navigation-course-id") != selected_course_id:
        st.session_state["_active-navigation-course-id"] = selected_course_id
        st.session_state.pop("navigation-top-level-id", None)
        st.session_state.pop("navigation-child-id", None)

    items = service.list_curriculum_items(selected_course.code)
    items_by_id = {str(item.id): item for item in items}
    top_level_items = _top_level_items(items)
    top_level_ids = [str(item.id) for item in top_level_items]
    if not top_level_ids:
        st.warning("This course has no top-level curriculum items.")
        return

    pending_code = st.session_state.pop("_pending-navigation-code", None)
    if pending_code is not None:
        parent, child = _resolve_navigation_target(items, pending_code)
        st.session_state["navigation-top-level-id"] = str(parent.id)
        st.session_state["navigation-child-id"] = (
            str(child.id) if child is not None else None
        )

    if st.session_state.get("navigation-top-level-id") not in top_level_ids:
        st.session_state["navigation-top-level-id"] = top_level_ids[0]
    selected_parent_id = st.selectbox(
        "Top-level item",
        options=top_level_ids,
        format_func=lambda item_id: _safe_item_label(items_by_id[item_id]),
        key="navigation-top-level-id",
    )
    selected_parent = items_by_id[selected_parent_id]

    descendants = _descendant_items(items, selected_parent.id)
    selected_child: CurriculumItem | None = None
    if descendants:
        descendant_ids = [str(item.id) for item in descendants]
        child_options: list[str | None] = [None, *descendant_ids]
        if st.session_state.get("navigation-child-id") not in child_options:
            st.session_state["navigation-child-id"] = None
        selected_child_id = st.selectbox(
            "Child item",
            options=child_options,
            format_func=lambda item_id: (
                "Use top-level item"
                if item_id is None
                else _isolated_code(
                    _local_item_code(items_by_id[item_id].code)
                )
            ),
            key="navigation-child-id",
        )
        if selected_child_id is not None:
            selected_child = items_by_id[selected_child_id]
            st.caption("Selected child title")
            _render_bidi_value(selected_child.title)
    else:
        st.session_state.pop("navigation-child-id", None)
        st.caption("This top-level item has no child items.")

    selected_item = selected_child or selected_parent
    st.caption(
        f"{len(top_level_items)} top-level items · "
        f"{len(descendants)} child items under this selection"
    )

    st.divider()
    workspace = service.show_item(selected_item.code)
    _render_item_workspace(service, workspace)


def _render_setup_sidebar() -> tuple[str, WorkspaceService]:
    with st.sidebar:
        st.header("Workspace setup")
        database_url = st.text_input(
            "Database URL",
            value=default_database_url(),
            help="The default creates academic_os.db in the project folder.",
        )
        service = _build_service(database_url)

        if st.button("Initialize database", use_container_width=True):
            try:
                service.initialize_database()
            except (OSError, ValueError) as error:
                st.error(str(error))
            else:
                _flash_and_rerun("Database is ready.")

        st.divider()
        st.subheader("Import curriculum")
        uploaded_file = st.file_uploader(
            "Curriculum JSON",
            type=["json"],
        )
        institution_name = st.text_input(
            "Institution",
            value=DEFAULT_INSTITUTION_NAME,
        )
        degree_name = st.text_input(
            "Degree",
            value=DEFAULT_DEGREE_NAME,
        )
        if st.button(
            "Import curriculum",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None,
        ):
            _import_uploaded_curriculum(
                service,
                uploaded_file,
                institution_name=institution_name,
                degree_name=degree_name,
            )

        st.divider()
        st.caption(
            "Temporary Streamlit interface for workflow validation. "
            "It is not the permanent frontend."
        )
    return database_url, service


def _import_uploaded_curriculum(
    service: WorkspaceService,
    uploaded_file: Any,
    *,
    institution_name: str,
    degree_name: str,
) -> None:
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=".json", delete=False) as temporary_file:
            temporary_file.write(uploaded_file.getvalue())
            temporary_path = Path(temporary_file.name)

        summary = service.import_curriculum(
            temporary_path,
            institution_name=institution_name,
            degree_name=degree_name,
        )
    except (OSError, ValueError, OperationalError) as error:
        st.error(str(error))
    else:
        _flash_and_rerun(
            f"Imported {summary.course_count} courses and "
            f"{summary.curriculum_item_count} curriculum items."
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _render_item_workspace(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    item = workspace.item
    _render_workspace_heading(item.title)

    code_column, course_column = st.columns([1, 3])
    with code_column:
        st.caption("Item code")
        _render_code(item.code)
    with course_column:
        st.caption("Course")
        _render_bidi_value(workspace.course.title)

    with st.container(border=True):
        source_column, pages_column = st.columns(2)
        with source_column:
            st.caption("Source")
            _render_bidi_value(item.source or "—")
        with pages_column:
            st.caption("Pages")
            _render_code(item.pages or "—")

        st.caption("Parent")
        if workspace.parent is None:
            st.write("Root item")
        else:
            _render_item_reference(workspace.parent, key_prefix="parent")

    if workspace.children:
        with st.expander(
            f"Child items ({len(workspace.children)})",
            expanded=True,
        ):
            for child in workspace.children:
                _render_item_reference(child, key_prefix="child")

    active_section = st.radio(
        "Workspace section",
        options=["Study tasks", "Notes", "Study history", "Progress"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"workspace-section-{item.id}",
    )
    if active_section == "Study tasks":
        _render_tasks(service, workspace)
    elif active_section == "Notes":
        _render_notes(service, workspace)
    elif active_section == "Study history":
        _render_study_sessions(service, workspace)
    else:
        _render_progress(service, workspace)


def _render_tasks(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    st.markdown("#### What can I do with this item right now?")
    if not workspace.tasks:
        st.info("Create a focused reading-to-review workflow.")
    if st.button(
        "Create default tasks",
        key=f"create-tasks-{workspace.item.id}",
    ):
        try:
            service.create_default_tasks(workspace.item.code)
        except WorkspaceError as error:
            st.error(str(error))
        else:
            _flash_and_rerun("Default study tasks are ready.")

    for task in workspace.tasks:
        details_column, action_column = st.columns([4, 1])
        with details_column:
            if task.completed_at is None:
                st.write(f"○ **{task.title}** · {task.task_type.code}")
            else:
                st.write(f"✓ ~~{task.title}~~ · {task.task_type.code}")
                st.caption(
                    f"Completed {task.completed_at:%Y-%m-%d %H:%M}"
                )
        with action_column:
            if task.completed_at is None and st.button(
                "Complete",
                key=f"complete-task-{task.id}",
                use_container_width=True,
            ):
                try:
                    service.complete_task(task.id)
                except WorkspaceError as error:
                    st.error(str(error))
                else:
                    _flash_and_rerun(f"Completed: {task.title}")


def _render_notes(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    with st.form(f"note-form-{workspace.item.id}", clear_on_submit=True):
        content = st.text_area(
            "New note",
            placeholder="Capture the idea you want to remember…",
        )
        submitted = st.form_submit_button("Add note", type="primary")
    if submitted:
        try:
            service.add_note(workspace.item.code, content)
        except WorkspaceError as error:
            st.error(str(error))
        else:
            _flash_and_rerun("Note added.")

    if not workspace.notes:
        st.caption("No notes yet.")
    for note in workspace.notes:
        st.markdown(f"> {note.content}")
        st.caption(note.created_at.strftime("%Y-%m-%d %H:%M"))


def _render_study_sessions(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    minutes = st.number_input(
        "Minutes studied",
        min_value=1,
        max_value=720,
        value=30,
        step=5,
        key=f"session-minutes-{workspace.item.id}",
    )
    if st.button(
        "Log study session",
        key=f"log-session-{workspace.item.id}",
        type="primary",
    ):
        try:
            service.log_study_session(
                workspace.item.code,
                minutes=int(minutes),
            )
        except WorkspaceError as error:
            st.error(str(error))
        else:
            _flash_and_rerun(f"Logged {int(minutes)} study minutes.")

    if not workspace.study_sessions:
        st.caption("No study sessions logged yet.")
    for session in workspace.study_sessions:
        duration = _session_duration_minutes(
            session.started_at,
            session.ended_at,
        )
        st.write(
            f"**{duration} minutes** · "
            f"{session.started_at:%Y-%m-%d %H:%M}"
        )


def _render_progress(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    current_status = (
        workspace.progress.status.code
        if workspace.progress is not None
        else StudyProgressStatus.NOT_STARTED
    )
    selected_status = st.selectbox(
        "Current progress",
        options=PROGRESS_STATUSES,
        index=PROGRESS_STATUSES.index(current_status),
        format_func=lambda status: status.replace("_", " ").title(),
        key=f"progress-{workspace.item.id}",
    )
    if st.button(
        "Update progress",
        key=f"update-progress-{workspace.item.id}",
        type="primary",
    ):
        try:
            service.set_progress(workspace.item.code, selected_status)
        except WorkspaceError as error:
            st.error(str(error))
        else:
            _flash_and_rerun(
                f"Progress updated to "
                f"{selected_status.replace('_', ' ')}."
            )


def _session_duration_minutes(
    started_at: datetime,
    ended_at: datetime | None,
) -> int:
    if ended_at is None:
        return 0
    return max(0, round((ended_at - started_at).total_seconds() / 60))


def _top_level_items(
    items: list[CurriculumItem],
) -> tuple[CurriculumItem, ...]:
    return tuple(
        sorted(
            (item for item in items if item.parent_id is None),
            key=lambda item: (item.order, item.code.casefold()),
        )
    )


def _descendant_items(
    items: list[CurriculumItem],
    parent_id: UUID,
) -> tuple[CurriculumItem, ...]:
    children_by_parent: dict[UUID, list[CurriculumItem]] = {}
    for item in items:
        if item.parent_id is not None:
            children_by_parent.setdefault(item.parent_id, []).append(item)
    for children in children_by_parent.values():
        children.sort(key=lambda item: (item.order, item.code.casefold()))

    descendants: list[CurriculumItem] = []

    def append_children(current_parent_id: UUID) -> None:
        for child in children_by_parent.get(current_parent_id, []):
            descendants.append(child)
            append_children(child.id)

    append_children(parent_id)
    return tuple(descendants)


def _resolve_navigation_target(
    items: list[CurriculumItem],
    target_code: str,
) -> tuple[CurriculumItem, CurriculumItem | None]:
    items_by_id = {item.id: item for item in items}
    target = next(
        (item for item in items if item.code == target_code),
        None,
    )
    if target is None:
        raise WorkspaceError(f"Curriculum item '{target_code}' was not found")

    root = target
    visited: set[UUID] = set()
    while root.parent_id is not None:
        if root.id in visited:
            raise WorkspaceError("Curriculum hierarchy contains a cycle")
        visited.add(root.id)
        parent = items_by_id.get(root.parent_id)
        if parent is None:
            raise WorkspaceError(
                f"Parent for curriculum item '{root.code}' was not found"
            )
        root = parent
    return root, None if root.id == target.id else target


def _local_item_code(code: str) -> str:
    _, separator, local_code = code.partition("-")
    return local_code if separator else code


def _safe_item_label(item: CurriculumItem) -> str:
    return (
        f"{_isolated_code(item.code)}  ·  "
        f"{FIRST_STRONG_ISOLATE}{item.title}{POP_DIRECTIONAL_ISOLATE}"
    )


def _isolated_code(code: str) -> str:
    return (
        f"{LEFT_TO_RIGHT_ISOLATE}{code}{POP_DIRECTIONAL_ISOLATE}"
    )


def _render_code(code: str) -> None:
    st.markdown(
        f'<span class="item-code" dir="ltr">{escape(code)}</span>',
        unsafe_allow_html=True,
    )


def _render_workspace_heading(title: str) -> None:
    st.markdown(
        f'<h2 class="workspace-title" dir="auto">{escape(title)}</h2>',
        unsafe_allow_html=True,
    )


def _render_bidi_value(value: str) -> None:
    st.markdown(
        f'<div class="bidi-value" dir="auto">{escape(value)}</div>',
        unsafe_allow_html=True,
    )


def _render_item_reference(
    item: CurriculumItem,
    *,
    key_prefix: str,
) -> None:
    code_column, title_column = st.columns([1, 4])
    with code_column:
        if st.button(
            _isolated_code(_local_item_code(item.code)),
            key=f"navigate-{key_prefix}-{item.id}",
            use_container_width=True,
        ):
            st.session_state["_pending-navigation-code"] = item.code
            st.rerun()
    with title_column:
        _render_bidi_value(item.title)


def _flash_and_rerun(message: str) -> None:
    st.session_state["workspace_flash"] = message
    st.rerun()


def _render_flash_message() -> None:
    message = st.session_state.pop("workspace_flash", None)
    if message:
        st.success(message)


def _apply_workspace_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem;}
        .bidi-value {
            unicode-bidi: plaintext;
            text-align: start;
            font-size: 1rem;
        }
        .workspace-title {
            unicode-bidi: plaintext;
            text-align: start;
            overflow-wrap: anywhere;
            margin: 0 0 1rem;
        }
        .item-code {
            direction: ltr;
            unicode-bidi: isolate;
            font-family: var(--font-monospace);
            white-space: nowrap;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] h3 {
            unicode-bidi: plaintext;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    run()
