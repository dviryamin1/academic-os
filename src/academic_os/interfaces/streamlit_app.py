from datetime import datetime
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import streamlit as st
from sqlalchemy.exc import OperationalError

from academic_os.application.services import (
    CourseProgressSummary,
    ItemWorkspace,
    OpenTask,
    StudyWorkflowService,
    WorkspaceError,
    WorkspaceService,
)
from academic_os.domain import Course, CurriculumItem, StudyProgressStatus
from academic_os.interfaces.streamlit.navigation import (
    NavigationEntry,
    filter_navigation_entries,
    flatten_hierarchy,
    preserved_item_code,
)
from academic_os.interfaces.streamlit.rtl import (
    isolated_code,
    isolated_title,
    local_item_code,
)
from academic_os.interfaces.streamlit.view_models import (
    recommendation_card,
    resume_card,
    schema_error_message,
)
from academic_os.interfaces.streamlit_bootstrap import (
    build_study_workflow_service,
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

# These keys intentionally survive Streamlit reruns. PENDING_ITEM_CODE_KEY
# distinguishes explicit navigation from a manual course change.
ACTIVE_ITEM_CODE_KEY = "active-item-code"
NAVIGATION_COURSE_KEY = "navigation-course-id"
NAVIGATION_SEARCH_KEY = "navigation-search"
WORKSPACE_SECTION_KEY = "workspace-section"
RENDERED_COURSE_KEY = "_rendered-navigation-course-id"
PENDING_ITEM_CODE_KEY = "_pending-navigation-code"
PENDING_COURSE_ID_KEY = "_pending-navigation-course-id"


@st.cache_resource
def _build_service(database_url: str) -> WorkspaceService:
    return build_workspace_service(database_url)


@st.cache_resource
def _build_workflow_service(database_url: str) -> StudyWorkflowService:
    return build_study_workflow_service(database_url)


def run() -> None:
    st.set_page_config(
        page_title="Academic OS",
        page_icon="📚",
        layout="wide",
    )
    _apply_workspace_style()

    st.title("Academic OS")
    st.caption("Your focused daily study workspace.")

    database_url, service = _render_setup_sidebar()
    _render_flash_message()

    try:
        courses = service.list_courses()
    except OperationalError as error:
        _render_database_error(error)
        return

    if not courses:
        st.info(
            "No curriculum is available yet. Initialize the database and "
            "import curriculum JSON from the sidebar."
        )
        return

    workflow_service = _build_workflow_service(database_url)
    try:
        _restore_active_item_from_query(service, courses)
        _render_today(workflow_service)
        active_code = _render_navigation_sidebar(service, courses)
        if active_code is None:
            st.info("This course has no curriculum items.")
            return
        workspace = service.show_item(active_code)
    except OperationalError as error:
        _render_database_error(error)
        return

    _render_item_workspace(service, workspace)


def _render_setup_sidebar() -> tuple[str, WorkspaceService]:
    with st.sidebar:
        st.header("Setup")
        database_url = st.text_input(
            "Database URL",
            value=default_database_url(),
            help="The default uses academic_os.db in the project folder.",
        )
        service = _build_service(database_url)

        initialize_column, upgrade_column = st.columns(2)
        if initialize_column.button(
            "Initialize",
            use_container_width=True,
            help="Create the schema and apply all migrations.",
        ):
            _run_database_upgrade(service, "Database is ready.")
        if upgrade_column.button(
            "Upgrade",
            use_container_width=True,
            help="Apply pending migrations without deleting data.",
        ):
            _run_database_upgrade(service, "Database upgraded successfully.")

        with st.expander("Import curriculum", expanded=False):
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
    return database_url, service


def _run_database_upgrade(
    service: WorkspaceService,
    success_message: str,
) -> None:
    try:
        service.initialize_database()
    except (OSError, ValueError, OperationalError) as error:
        st.error(str(error))
    else:
        _flash_and_rerun(success_message)


def _render_navigation_sidebar(
    service: WorkspaceService,
    courses: list[Course],
) -> str | None:
    with st.sidebar:
        st.divider()
        st.header("Navigate")
        courses_by_id = {str(course.id): course for course in courses}
        course_ids = list(courses_by_id)
        pending_course_id = st.session_state.pop(
            PENDING_COURSE_ID_KEY,
            None,
        )
        pending_code = st.session_state.pop(PENDING_ITEM_CODE_KEY, None)
        if pending_course_id in course_ids:
            st.session_state[NAVIGATION_COURSE_KEY] = pending_course_id
        if st.session_state.get(NAVIGATION_COURSE_KEY) not in course_ids:
            st.session_state[NAVIGATION_COURSE_KEY] = course_ids[0]

        selected_course_id = st.selectbox(
            "Course",
            options=course_ids,
            format_func=lambda course_id: courses_by_id[course_id].title,
            key=NAVIGATION_COURSE_KEY,
        )
        previous_course_id = st.session_state.get(RENDERED_COURSE_KEY)
        if (
            previous_course_id is not None
            and previous_course_id != selected_course_id
            and pending_code is None
        ):
            st.session_state.pop(ACTIVE_ITEM_CODE_KEY, None)
        st.session_state[RENDERED_COURSE_KEY] = selected_course_id

        selected_course = courses_by_id[selected_course_id]
        entries = flatten_hierarchy(
            service.list_curriculum_items(selected_course.code)
        )
        if not entries:
            st.caption("No curriculum items in this course.")
            return None

        if pending_code is not None:
            st.session_state[ACTIVE_ITEM_CODE_KEY] = pending_code
        active_code = preserved_item_code(
            entries,
            st.session_state.get(ACTIVE_ITEM_CODE_KEY),
        )
        st.session_state[ACTIVE_ITEM_CODE_KEY] = active_code
        if st.query_params.get("item") != active_code:
            st.query_params["item"] = active_code

        query = st.text_input(
            "Search items",
            key=NAVIGATION_SEARCH_KEY,
            placeholder="Code, Hebrew title, or pages",
        )
        if query.strip():
            matches = filter_navigation_entries(entries, query)
            st.caption(f"{len(matches)} matches")
            if not matches:
                st.info("No curriculum items match this search.")
            for entry in matches[:30]:
                _render_navigation_entry(entry, active_code, search_result=True)
        else:
            st.caption("Browse hierarchy")
            for branch in _hierarchy_branches(entries):
                root = branch[0]
                with st.expander(
                    isolated_title(root.item.title),
                    expanded=root.item.code == active_code,
                ):
                    for entry in branch:
                        _render_navigation_entry(entry, active_code)
        return active_code


def _hierarchy_branches(
    entries: tuple[NavigationEntry, ...],
) -> tuple[tuple[NavigationEntry, ...], ...]:
    branches: list[list[NavigationEntry]] = []
    for entry in entries:
        if entry.depth == 0 or not branches:
            branches.append([entry])
        else:
            branches[-1].append(entry)
    return tuple(tuple(branch) for branch in branches)


def _render_navigation_entry(
    entry: NavigationEntry,
    active_code: str | None,
    *,
    search_result: bool = False,
) -> None:
    code_column, title_column = st.columns([1.3, 2.7])
    with code_column:
        marker = "✓ " if entry.item.code == active_code else ""
        depth_marker = "" if search_result else "↳ " * entry.depth
        if st.button(
            marker
            + depth_marker
            + isolated_code(local_item_code(entry.item.code)),
            key=f"sidebar-item-{entry.item.id}",
            use_container_width=True,
        ):
            _activate_item(entry.item)
    with title_column:
        if entry.depth == 0 and not search_result:
            st.markdown(
                f'<div class="bidi-value root-item-title" dir="auto">'
                f"{escape(entry.item.title)}</div>",
                unsafe_allow_html=True,
            )
        else:
            _render_bidi_value(entry.item.title)


def _render_today(service: StudyWorkflowService) -> None:
    st.subheader("Today")
    resume = service.resume_learning()
    recommendation = service.recommend_next()

    resume_column, recommendation_column = st.columns(2)
    with resume_column:
        with st.container(border=True):
            st.markdown("#### Resume learning")
            if resume is None:
                st.info(
                    "No study activity yet. Open an item and log a session "
                    "or update its progress."
                )
            else:
                card = resume_card(resume)
                _render_code(card.item_code)
                _render_bidi_value(card.item_title)
                _render_labeled_value("Course", card.course_title)
                _render_labeled_value("Pages", card.pages, code=True)
                session_text = (
                    f"{card.session_minutes} minutes"
                    if card.session_minutes is not None
                    else "Progress updated"
                )
                st.caption(
                    f"{card.activity_at:%Y-%m-%d %H:%M} · "
                    f"{session_text} · {card.open_task_count} open tasks"
                )
                if st.button(
                    "Open resume item",
                    key="open-resume-item",
                    type="primary",
                    use_container_width=True,
                ):
                    _activate_item(resume.item)

    with recommendation_column:
        with st.container(border=True):
            st.markdown("#### Recommended next task")
            if recommendation is None:
                st.info(
                    "No open tasks yet. Open an item and create its default "
                    "study tasks."
                )
            else:
                card = recommendation_card(recommendation)
                st.write(f"**{card.task_title}**")
                st.caption(card.task_type.replace("_", " ").title())
                _render_bidi_value(card.item_title)
                _render_labeled_value("Course", card.course_title)
                _render_labeled_value("Pages", card.pages, code=True)
                st.caption(card.reason)
                if st.button(
                    "Open recommended item",
                    key="open-recommended-item",
                    type="primary",
                    use_container_width=True,
                ):
                    _activate_item(recommendation.item)

    with st.expander("Open tasks", expanded=False):
        _render_open_tasks(service.list_open_tasks())

    with st.expander("Course progress", expanded=False):
        summaries = service.progress_summary()
        if summaries:
            st.dataframe(
                _progress_summary_rows(summaries),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No courses found.")

    st.divider()


def _render_open_tasks(open_tasks: list[OpenTask]) -> None:
    if not open_tasks:
        st.caption("No open study tasks.")
        return
    for result in open_tasks:
        details_column, action_column = st.columns([5, 1])
        with details_column:
            st.write(
                f"**{result.task.title}** · "
                f"{result.task.task_type.code}"
            )
            _render_code(result.item.code)
            _render_bidi_value(result.item.title)
            st.caption(result.course.title)
        with action_column:
            if st.button(
                "Open",
                key=f"open-task-item-{result.task.id}",
                use_container_width=True,
            ):
                _activate_item(result.item)


def _render_item_workspace(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    item = workspace.item
    st.caption("ACTIVE ITEM")
    _render_workspace_heading(item.title)

    code_column, course_column, progress_column = st.columns([1, 3, 1.5])
    with code_column:
        _render_labeled_value("Item code", item.code, code=True)
    with course_column:
        _render_labeled_value("Course", workspace.course.title)
    with progress_column:
        progress_status = (
            workspace.progress.status.code
            if workspace.progress is not None
            else StudyProgressStatus.NOT_STARTED
        )
        _render_labeled_value(
            "Progress",
            progress_status.replace("_", " ").title(),
        )

    with st.container(border=True):
        source_column, pages_column = st.columns(2)
        with source_column:
            _render_labeled_value("Source", item.source or "—")
        with pages_column:
            _render_labeled_value("Pages", item.pages or "—", code=True)

        relation_column, children_column = st.columns(2)
        with relation_column:
            st.caption("Parent")
            if workspace.parent is None:
                st.write("Root item")
            else:
                _render_item_reference(workspace.parent, key_prefix="parent")
        with children_column:
            st.caption(f"Children ({len(workspace.children)})")
            if not workspace.children:
                st.write("No child items")
            else:
                st.write("Browse child items in the sidebar hierarchy.")

    active_section = st.radio(
        "Workspace section",
        options=["Tasks", "Notes", "Study session", "Progress"],
        horizontal=True,
        label_visibility="collapsed",
        key=WORKSPACE_SECTION_KEY,
    )
    if active_section == "Tasks":
        _render_tasks(service, workspace)
    elif active_section == "Notes":
        _render_notes(service, workspace)
    elif active_section == "Study session":
        _render_study_sessions(service, workspace)
    else:
        _render_progress(service, workspace)


def _render_tasks(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    st.markdown("#### Tasks")
    if not workspace.tasks:
        st.info(
            "No tasks yet. Create the default reading-to-review workflow."
        )
    if st.button(
        "Create missing default tasks",
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
            status = "Completed" if task.completed_at is not None else "Open"
            st.write(f"**{task.title}**")
            st.caption(
                f"{task.task_type.code.replace('_', ' ').title()} · {status}"
            )
            if task.completed_at is not None:
                st.caption(f"Completed {task.completed_at:%Y-%m-%d %H:%M}")
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
    st.markdown("#### Notes")
    with st.form(f"note-form-{workspace.item.id}", clear_on_submit=True):
        content = st.text_area(
            "New note",
            placeholder="כתוב כאן רעיון שחשוב לזכור…",
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
        st.markdown(
            f'<div class="note-card" dir="auto">{escape(note.content)}</div>',
            unsafe_allow_html=True,
        )
        st.caption(note.created_at.strftime("%Y-%m-%d %H:%M"))


def _render_study_sessions(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    st.markdown("#### Study session")
    st.caption("Log common durations with one click.")
    quick_columns = st.columns(4)
    for column, minutes in zip(quick_columns, (15, 30, 45, 60), strict=True):
        if column.button(
            f"{minutes} min",
            key=f"quick-session-{workspace.item.id}-{minutes}",
            use_container_width=True,
        ):
            _log_session(service, workspace.item.code, minutes)

    custom_column, action_column = st.columns([3, 1])
    with custom_column:
        custom_minutes = st.number_input(
            "Custom minutes",
            min_value=1,
            max_value=720,
            value=30,
            step=5,
            key=f"session-minutes-{workspace.item.id}",
        )
    with action_column:
        st.write("")
        st.write("")
        if st.button(
            "Log session",
            key=f"log-session-{workspace.item.id}",
            type="primary",
            use_container_width=True,
        ):
            _log_session(service, workspace.item.code, int(custom_minutes))

    if not workspace.study_sessions:
        st.caption("No study sessions yet. Log your first session.")
    for session in workspace.study_sessions[:10]:
        duration = _session_duration_minutes(
            session.started_at,
            session.ended_at,
        )
        st.write(
            f"**{duration} minutes** · "
            f"{session.started_at:%Y-%m-%d %H:%M}"
        )


def _log_session(
    service: WorkspaceService,
    item_code: str,
    minutes: int,
) -> None:
    try:
        service.log_study_session(item_code, minutes=minutes)
    except WorkspaceError as error:
        st.error(str(error))
    else:
        _flash_and_rerun(f"Logged {minutes} study minutes.")


def _render_progress(
    service: WorkspaceService,
    workspace: ItemWorkspace,
) -> None:
    st.markdown("#### Progress")
    if workspace.progress is None:
        current_status = StudyProgressStatus.NOT_STARTED
        st.info("Not started. Set a status when you begin this item.")
    else:
        current_status = workspace.progress.status.code
        st.caption(
            "Status last updated "
            f"{workspace.progress.status_updated_at:%Y-%m-%d %H:%M}"
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


def _activate_item(item: CurriculumItem) -> None:
    st.query_params["item"] = item.code
    st.session_state[ACTIVE_ITEM_CODE_KEY] = item.code
    st.session_state[PENDING_COURSE_ID_KEY] = str(item.course_id)
    st.session_state[PENDING_ITEM_CODE_KEY] = item.code
    st.rerun()


def _restore_active_item_from_query(
    service: WorkspaceService,
    courses: list[Course],
) -> None:
    if st.session_state.get(ACTIVE_ITEM_CODE_KEY) is not None:
        return
    requested_code = st.query_params.get("item")
    if not isinstance(requested_code, str) or not requested_code:
        return

    for course in courses:
        matching_item = next(
            (
                item
                for item in service.list_curriculum_items(course.code)
                if item.code == requested_code
            ),
            None,
        )
        if matching_item is not None:
            st.session_state[ACTIVE_ITEM_CODE_KEY] = matching_item.code
            st.session_state[PENDING_ITEM_CODE_KEY] = matching_item.code
            st.session_state[PENDING_COURSE_ID_KEY] = str(course.id)
            return


def _render_database_error(error: OperationalError) -> None:
    message = schema_error_message(error)
    if message is not None:
        st.error(message)
        st.caption(
            "Academic OS will not reset or delete the database automatically."
        )
    else:
        st.info(
            "The database is not initialized. Use Initialize in the sidebar."
        )


def _session_duration_minutes(
    started_at: datetime,
    ended_at: datetime | None,
) -> int:
    if ended_at is None:
        return 0
    return max(0, round((ended_at - started_at).total_seconds() / 60))


def _progress_summary_rows(
    summaries: list[CourseProgressSummary],
) -> list[dict[str, str | int]]:
    return [
        {
            "Course": summary.course.title,
            "Items": summary.total_items,
            "Not started": summary.not_started_items,
            "In progress": summary.in_progress_items,
            "Mastered": summary.mastered_items,
            "Open tasks": summary.open_tasks,
            "Completed tasks": summary.completed_tasks,
            "Study minutes": summary.total_study_minutes,
        }
        for summary in summaries
    ]


def _render_item_reference(
    item: CurriculumItem,
    *,
    key_prefix: str,
) -> None:
    code_column, title_column = st.columns([1, 3])
    with code_column:
        if st.button(
            isolated_code(local_item_code(item.code)),
            key=f"navigate-{key_prefix}-{item.id}",
            use_container_width=True,
        ):
            _activate_item(item)
    with title_column:
        _render_bidi_value(item.title)


def _render_labeled_value(
    label: str,
    value: str,
    *,
    code: bool = False,
) -> None:
    st.caption(label)
    if code:
        _render_code(value)
    else:
        _render_bidi_value(value)


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
        .block-container {padding-top: 1.5rem; max-width: 1200px;}
        .bidi-value {
            unicode-bidi: plaintext;
            text-align: start;
            overflow-wrap: anywhere;
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
            font-weight: 600;
            white-space: nowrap;
        }
        .root-item-title {
            font-size: 1.05rem;
            font-weight: 750;
            border-inline-start: 3px solid var(--primary-color);
            padding-inline-start: .5rem;
        }
        .note-card {
            unicode-bidi: plaintext;
            text-align: start;
            border-inline-start: 3px solid var(--primary-color);
            padding: .65rem .85rem;
            margin-top: .5rem;
            background: color-mix(in srgb, var(--primary-color) 7%, transparent);
            border-radius: .25rem;
        }
        [data-testid="stSidebar"] .stButton button {
            min-height: 2.2rem;
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
