# Academic OS — Sprint 2B Import and First Usable Workspace

## Implemented workflow

Sprint 2B provides a local CLI that:

1. applies database migrations;
2. imports the supplied curriculum JSON;
3. lists courses and course curriculum items;
4. displays one item with source, pages, parent, children, tasks, and progress;
5. creates reading, summary, practice, and review tasks;
6. completes an immutable task through repository replacement;
7. adds notes;
8. logs completed study time;
9. creates or updates study progress.

## Commands

```text
academic-os init-db
academic-os import-curriculum PATH
academic-os list-courses
academic-os list-items --course COURSE
academic-os show-item ITEM_CODE
academic-os create-default-tasks ITEM_CODE
academic-os complete-task TASK_UUID
academic-os add-note ITEM_CODE CONTENT
academic-os log-session ITEM_CODE --minutes MINUTES
academic-os set-progress ITEM_CODE STATUS
```

All data commands support a global `--database-url` option before the command.
Otherwise `ACADEMIC_OS_DATABASE_URL` or `sqlite:///academic_os.db` is used.

## Architecture

- `JsonCurriculumImporter` reads and maps UTF-8 JSON in Infrastructure.
- `CurriculumImportResult` carries the complete mapped graph without
  persistence side effects.
- `WorkspaceService` owns workflow orchestration and transaction boundaries.
- SQLAlchemy repositories remain persistence-only adapters.
- The CLI is an Interface-layer adapter with no ORM queries or JSON parsing.

Imported UUIDs are deterministic. Re-importing the same institution, degree,
and source updates matching records rather than duplicating them. Default task
and progress identifiers are also deterministic.

## Migration

Alembic revision `0002` adds:

- `curriculum_items.code`, required and human-readable;
- `curriculum_items.pages`, optional text.

UUID remains the database primary key. The published initial migration is
unchanged.

## Test coverage

The 20-test suite covers:

- JSON parsing and deterministic mapping;
- Hebrew value preservation;
- parent-child hierarchy;
- migration upgrade, downgrade, and metadata parity;
- course and item queries;
- item workspace display;
- default task creation and idempotency;
- task completion;
- notes;
- study sessions;
- progress creation and update;
- all CLI workflow commands;
- persistence rollback and domain independence.

## Limitations

- JSON `part` is not stored because it is not required by the approved domain or
  workspace. `level` is represented by hierarchy and `order` by sibling order.
- Course codes are derived from a shared item-code prefix. If no shared prefix
  exists, a deterministic synthetic code is used.
- `show-item` requires item codes to be unambiguous across imported courses and
  reports an error if the same code exists in multiple courses.
- Re-import updates matching records but does not delete database items removed
  from a later source file.
- Notes and sessions can be added but do not yet have dedicated list commands.
- Datetimes use local process time because no timezone policy is approved.
- There is no API, web UI, authentication, AI, planner, scheduling, or
  dashboard.

