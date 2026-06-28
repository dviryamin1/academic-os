# Academic OS — Sprint 2 Persistence Foundation

## 1. Updated project structure

```text
Academic OS/
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
├── src/academic_os/
│   ├── application/ports/
│   │   ├── curriculum_importer.py
│   │   ├── repositories.py
│   │   └── unit_of_work.py
│   ├── domain/
│   │   ├── entities/
│   │   └── value_objects/
│   └── infrastructure/persistence/sqlalchemy/
│       ├── database.py
│       ├── mappers.py
│       ├── models.py
│       ├── repositories.py
│       └── unit_of_work.py
└── tests/
    ├── persistence/
    │   ├── conftest.py
    │   ├── test_migrations.py
    │   └── test_persistence.py
    └── test_architecture.py
```

## 2. Database schema diagram

```mermaid
erDiagram
    INSTITUTIONS {
        uuid id PK
        string name
    }
    DEGREES {
        uuid id PK
        uuid institution_id FK
        string name
    }
    ACADEMIC_YEARS {
        uuid id PK
        uuid degree_id FK
        string label
        date start_date
        date end_date
    }
    SEMESTERS {
        uuid id PK
        uuid academic_year_id FK
        string name
        date start_date
        date end_date
    }
    COURSES {
        uuid id PK
        uuid institution_id FK
        string code
        string title
    }
    DEGREE_COURSES {
        uuid id PK
        uuid degree_id FK
        uuid course_id FK
        decimal credits
    }
    CURRICULUM_ITEMS {
        uuid id PK
        uuid parent_id FK
        uuid course_id FK
        string title
        string item_type
        string source
        int order
    }
    STUDY_PLANS {
        uuid id PK
        uuid semester_id FK
    }
    STUDY_PLAN_ITEMS {
        uuid id PK
        uuid study_plan_id FK
        uuid curriculum_item_id FK
    }
    STUDY_TASKS {
        uuid id PK
        uuid curriculum_item_id FK
        string task_type
        string title
        datetime due_at
        datetime completed_at
    }
    STUDY_SESSIONS {
        uuid id PK
        uuid curriculum_item_id FK
        datetime started_at
        datetime ended_at
    }
    STUDY_PROGRESS {
        uuid id PK
        uuid curriculum_item_id FK
        string status
    }
    NOTES {
        uuid id PK
        uuid curriculum_item_id FK
        string content
        datetime created_at
    }
    ASSIGNMENTS {
        uuid id PK
        uuid course_id FK
        string title
        datetime due_at
    }
    EXAMS {
        uuid id PK
        uuid course_id FK
        string title
        datetime starts_at
    }
    EVENTS {
        uuid id PK
        string title
        datetime starts_at
        datetime ends_at
    }

    INSTITUTIONS ||--o{ DEGREES : offers
    INSTITUTIONS ||--o{ COURSES : owns
    DEGREES ||--o{ ACADEMIC_YEARS : contains
    ACADEMIC_YEARS ||--o{ SEMESTERS : contains
    DEGREES ||--o{ DEGREE_COURSES : includes
    COURSES ||--o{ DEGREE_COURSES : belongs_to
    COURSES ||--o{ CURRICULUM_ITEMS : contains
    CURRICULUM_ITEMS o|--o{ CURRICULUM_ITEMS : parent_of
    SEMESTERS ||--o{ STUDY_PLANS : has
    STUDY_PLANS ||--o{ STUDY_PLAN_ITEMS : contains
    CURRICULUM_ITEMS ||--o{ STUDY_PLAN_ITEMS : referenced_by
    CURRICULUM_ITEMS ||--o{ STUDY_TASKS : targeted_by
    CURRICULUM_ITEMS ||--o{ STUDY_SESSIONS : studied_in
    CURRICULUM_ITEMS ||--o| STUDY_PROGRESS : tracked_by
    CURRICULUM_ITEMS ||--o{ NOTES : documented_by
    COURSES ||--o{ ASSIGNMENTS : assessed_by
    COURSES ||--o{ EXAMS : examined_by
```

The schema enforces the approved one-to-one curriculum progress relationship.
No additional domain uniqueness or text-length rules were inferred at the
persistence boundary.

## 3. Repository overview

`Repository[T]` is an application-layer port with four persistence operations:

- `add(entity)`
- `get(entity_id)`
- `list_all()`
- `remove(entity_id)`

`SqlAlchemyRepository` implements this port using an injected SQLAlchemy session
and an explicit mapper. The generic implementation avoids 16 duplicated
repository classes while the Unit of Work exposes a clearly named repository
for every approved domain entity.

`UnitOfWork` is the application-layer transaction contract.
`SqlAlchemyUnitOfWork`:

- opens one session and transaction on entry;
- exposes all entity repositories;
- commits only when explicitly requested;
- supports explicit rollback;
- rolls back uncommitted work and closes the session on exit.

## 4. Alembic migration summary

Revision `0001` creates all 16 approved entity tables, their primary keys,
foreign keys, relationship indexes, and approved uniqueness constraints. It
contains no seed data or inserts.

Alembic uses the same `ACADEMIC_OS_DATABASE_URL` configuration as normal session
creation. The default is `sqlite:///academic_os.db`; another SQLAlchemy URL can
be supplied without changing mappings or migration code.

The migration was upgraded and downgraded on a new isolated database and checked
against the ORM metadata with Alembic's schema-drift check.

## 5. Testing summary

The complete suite contains 13 passing tests. Persistence coverage verifies:

- round-trip persistence for every approved domain entity;
- domain value-object conversion;
- approved ORM relationships;
- unlimited curriculum hierarchy through `parent_id`;
- repository add, get, list, and remove behavior;
- automatic transaction rollback when work is not committed;
- initial migration creation and ORM schema consistency;
- continued domain independence from SQLAlchemy, Alembic, SQLite, and
  infrastructure modules.

The Event persistence regression test covers both a nullable `ends_at` value and
a concrete end time. `Event`, `EventModel`, `EVENT_MAPPER`, and migration `0001`
all represent this field consistently. Alembic's schema-drift check protects
this model/migration parity.

Every persistence test uses a fresh SQLite database inside pytest's isolated
temporary workspace. The default application database is never created or used.

## 6. Architectural decisions

- Domain classes remain unchanged and framework-independent.
- ORM classes are separate persistence records with no business methods.
- Explicit mapper objects convert between immutable domain entities and ORM
  records.
- SQLAlchemy's portable `Uuid`, `Date`, `DateTime`, and `Numeric` types avoid
  SQLite-only schema definitions.
- Value objects are stored by their stable string codes and reconstructed at the
  mapper boundary.
- Database configuration is centralized in `database.py` and shared with
  Alembic.
- SQLite foreign-key enforcement is enabled only at the SQLite connection
  boundary; other database engines are unaffected.
- No delete cascades were introduced because deletion behavior is a domain
  decision that has not been approved.
- The existing `CurriculumImporter` interface remains untouched and has no
  implementation.
