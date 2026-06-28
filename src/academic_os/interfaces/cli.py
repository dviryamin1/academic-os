import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import OperationalError

from academic_os.application.services import WorkspaceError, WorkspaceService
from academic_os.domain import StudyProgressStatus
from academic_os.infrastructure.importers import JsonCurriculumImporter
from academic_os.infrastructure.persistence.sqlalchemy import (
    SqlAlchemyUnitOfWork,
    create_database_engine,
    create_session_factory,
    get_database_url,
    upgrade_database,
)

DEFAULT_INSTITUTION_NAME = "האוניברסיטה הפתוחה"
DEFAULT_DEGREE_NAME = "פסיכולוגיה"


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    database_url = arguments.database_url or get_database_url()

    try:
        if arguments.command == "init-db":
            upgrade_database(database_url)
            print("Database is ready.")
            print("Next: academic-os import-curriculum PATH")
            return 0

        engine = create_database_engine(database_url)
        try:
            session_factory = create_session_factory(engine)
            service = WorkspaceService(
                lambda: SqlAlchemyUnitOfWork(session_factory),
                JsonCurriculumImporter(),
            )
            return _run_command(arguments, service)
        finally:
            engine.dispose()
    except (WorkspaceError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except OperationalError:
        print(
            "Error: database is not initialized. Run: academic-os init-db",
            file=sys.stderr,
        )
        return 2


def _run_command(
    arguments: argparse.Namespace,
    service: WorkspaceService,
) -> int:
    if arguments.command == "import-curriculum":
        summary = service.import_curriculum(
            arguments.path,
            institution_name=arguments.institution_name,
            degree_name=arguments.degree_name,
        )
        print(
            f"Imported {summary.course_count} courses and "
            f"{summary.curriculum_item_count} curriculum items."
        )
        print("Next: academic-os list-courses")
        return 0

    if arguments.command == "list-courses":
        courses = service.list_courses()
        if not courses:
            print("No courses found.")
            print("Next: academic-os import-curriculum PATH")
            return 0
        for course in courses:
            print(f"{course.code}\t{course.title}")
        print('Next: academic-os list-items --course "COURSE NAME"')
        return 0

    if arguments.command == "list-items":
        items = service.list_curriculum_items(arguments.course)
        for item in items:
            pages = f" (pages {item.pages})" if item.pages else ""
            print(f"{item.code}\t{item.title}{pages}")
        print("Next: academic-os show-item ITEM_CODE")
        return 0

    if arguments.command == "show-item":
        workspace = service.show_item(arguments.item_code)
        item = workspace.item
        print(f"[{item.code}] {item.title}")
        print(f"Course: {workspace.course.title}")
        print(f"Source: {item.source or '-'}")
        print(f"Pages: {item.pages or '-'}")
        print(
            "Parent: "
            + (
                f"[{workspace.parent.code}] {workspace.parent.title}"
                if workspace.parent
                else "-"
            )
        )
        if workspace.children:
            print("Children:")
            for child in workspace.children:
                print(f"  [{child.code}] {child.title}")
        else:
            print("Children: -")
        print(
            "Progress: "
            + (
                workspace.progress.status.code
                if workspace.progress is not None
                else "not set"
            )
        )
        if workspace.tasks:
            print("Tasks:")
            for task in workspace.tasks:
                marker = "done" if task.completed_at is not None else "open"
                print(
                    f"  {task.id} [{marker}] "
                    f"{task.task_type.code}: {task.title}"
                )
        else:
            print("Tasks: none")
        print(f"Next: academic-os create-default-tasks {item.code}")
        return 0

    if arguments.command == "create-default-tasks":
        tasks = service.create_default_tasks(arguments.item_code)
        for task in tasks:
            marker = "done" if task.completed_at is not None else "open"
            print(f"{task.id}\t{task.task_type.code}\t{marker}")
        print("Next: academic-os complete-task TASK_ID")
        return 0

    if arguments.command == "complete-task":
        task = service.complete_task(arguments.task_id)
        print(f"Completed task {task.id}: {task.title}")
        return 0

    if arguments.command == "add-note":
        note = service.add_note(arguments.item_code, arguments.content)
        print(f"Added note {note.id} to {arguments.item_code}.")
        return 0

    if arguments.command == "log-session":
        session = service.log_study_session(
            arguments.item_code,
            minutes=arguments.minutes,
        )
        print(
            f"Logged {arguments.minutes} minutes for "
            f"{arguments.item_code} ({session.id})."
        )
        return 0

    if arguments.command == "set-progress":
        progress = service.set_progress(
            arguments.item_code,
            arguments.status,
        )
        print(
            f"Progress for {arguments.item_code}: {progress.status.code}"
        )
        return 0

    raise WorkspaceError(f"Unknown command: {arguments.command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="academic-os",
        description="Work with one Academic OS curriculum item at a time.",
    )
    parser.add_argument(
        "--database-url",
        help="SQLAlchemy database URL; defaults to ACADEMIC_OS_DATABASE_URL.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init-db", help="Apply database migrations.")

    import_parser = commands.add_parser(
        "import-curriculum",
        help="Import curriculum JSON.",
    )
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument(
        "--institution-name",
        default=DEFAULT_INSTITUTION_NAME,
    )
    import_parser.add_argument(
        "--degree-name",
        default=DEFAULT_DEGREE_NAME,
    )

    commands.add_parser("list-courses", help="List imported courses.")

    list_items_parser = commands.add_parser(
        "list-items",
        help="List curriculum items in a course.",
    )
    list_items_parser.add_argument("--course", required=True)

    show_item_parser = commands.add_parser(
        "show-item",
        help="Show one curriculum-item workspace.",
    )
    show_item_parser.add_argument("item_code")

    tasks_parser = commands.add_parser(
        "create-default-tasks",
        help="Create reading, summary, practice, and review tasks.",
    )
    tasks_parser.add_argument("item_code")

    complete_parser = commands.add_parser(
        "complete-task",
        help="Mark a study task completed.",
    )
    complete_parser.add_argument("task_id", type=UUID)

    note_parser = commands.add_parser("add-note", help="Add an item note.")
    note_parser.add_argument("item_code")
    note_parser.add_argument("content")

    session_parser = commands.add_parser(
        "log-session",
        help="Log completed study time.",
    )
    session_parser.add_argument("item_code")
    session_parser.add_argument("--minutes", type=int, required=True)

    progress_parser = commands.add_parser(
        "set-progress",
        help="Set item study progress.",
    )
    progress_parser.add_argument("item_code")
    progress_parser.add_argument(
        "status",
        choices=[
            StudyProgressStatus.NOT_STARTED,
            StudyProgressStatus.IN_PROGRESS,
            StudyProgressStatus.MASTERED,
        ],
    )

    return parser


if __name__ == "__main__":
    raise SystemExit(main())
