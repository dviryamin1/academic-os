from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import streamlit as st
from sqlalchemy.exc import OperationalError

from academic_os.application.services import (
    ItemWorkspace,
    WorkspaceError,
    WorkspaceService,
)
from academic_os.domain import StudyProgressStatus
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
    selected_course = st.selectbox(
        "Course",
        options=courses,
        format_func=lambda course: course.title,
    )
    items = service.list_curriculum_items(selected_course.code)
    selected_item = st.selectbox(
        "Curriculum item",
        options=items,
        format_func=lambda item: f"{item.code} · {item.title}",
    )
    st.caption(f"{len(items)} curriculum items in this course")

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
    st.subheader(item.title)
    st.caption(f"{item.code} · {workspace.course.title}")

    with st.container(border=True):
        st.markdown(f"**Course:** {workspace.course.title}")
        st.markdown(f"**Source:** {item.source or '—'}")
        st.markdown(f"**Pages:** {item.pages or '—'}")
        st.markdown(
            "**Parent:** "
            + (
                f"{workspace.parent.code} — {workspace.parent.title}"
                if workspace.parent
                else "Root item"
            )
        )

    if workspace.children:
        with st.expander(
            f"Child items ({len(workspace.children)})",
            expanded=False,
        ):
            for child in workspace.children:
                st.write(f"**{child.code}** — {child.title}")

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
