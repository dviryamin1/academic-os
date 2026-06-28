# Academic OS — Sprint 2B Pre-implementation Blockers

**Status:** Resolved by explicit user approval; Sprint 2B resumed.

## Supplied JSON

`course_catalog_hebrew_values.json` is valid UTF-8 JSON with:

- schema version `1.0`;
- 63 curriculum records;
- 3 Hebrew-named courses;
- 37 root items and 26 child items;
- item types: chapter, unit, section, subtopic, and article;
- stable item identifiers such as `DP-01` and `STAT-10.8`;
- a `pages` value for every item;
- record keys `id`, `parent_id`, `level`, `type`, `course`, `source`,
  `part`, `title`, and `pages`.

Hebrew values load correctly when the file is decoded as UTF-8.

## Blocker 1: CurriculumItem cannot support the required CLI

### Problem

The approved `CurriculumItem` contains an internal UUID, title, type, course,
source, order, and parent UUID. It does not contain:

- the stable user-facing item identifier from JSON;
- the page range required by `show-item`.

The required command `show-item STAT-10.8` cannot resolve that reference after
import, and the required item view cannot display pages.

Encoding either value into `source`, `title`, or the UUID would mix separate
domain concepts and make querying unreliable.

### Minimal proposed amendment

Add only:

```text
CurriculumItem.code: str
CurriculumItem.pages: str | None
```

`code` is the stable user-facing curriculum reference. `pages` remains text
because source ranges are not guaranteed to be single numeric intervals.

Persistence would require a new Alembic revision adding both columns. Migration
`0001` should remain unchanged because it has already been published.

No other domain fields are currently required. JSON `level` is represented by
the parent hierarchy, array position can supply `order`, and `part` is not
required by the approved workspace workflow.

## Blocker 2: CurriculumImporter cannot return the required import graph

### Problem

The existing port returns only:

```python
Iterable[CurriculumItem]
```

Sprint 2B requires one import operation to map and persist `Institution`,
`Degree`, `Course`, `DegreeCourse`, and `CurriculumItem`. A concrete importer
cannot provide that graph through the current contract without hidden database
side effects or infrastructure-specific APIs.

### Minimal proposed amendment

Change the application port to return a format-neutral import batch containing:

- one `Institution`;
- one `Degree`;
- the imported `Course` entities;
- their `DegreeCourse` associations;
- all `CurriculumItem` entities.

The JSON implementation remains in Infrastructure. File reading and JSON
parsing do not enter the Domain or Application layers.

## Blocker 3: Required ownership metadata is absent from JSON

### Problem

The file contains course titles but no institution, degree, or course codes.
Those fields are mandatory in the approved domain.

### Minimal proposed behavior

Require institution and degree names as import-command options:

```text
academic-os import-curriculum FILE \
  --institution "האוניברסיטה הפתוחה" \
  --degree "פסיכולוגיה"
```

Generate deterministic internal course codes from course titles rather than
hardcoding this catalog or inferring undocumented meaning from item prefixes.
Course selection remains title-based as required.

## Persistence contract adjustment

Completing an immutable `StudyTask` and changing immutable `StudyProgress`
requires replacing an existing persisted value. The current repository contract
supports add, get, list, and remove only.

The minimal persistence amendment is an `update(entity)` operation implemented
by the SQLAlchemy adapter. This changes no domain entity and contains no
business logic.

## Decisions required before implementation

Approval is required for:

1. adding `CurriculumItem.code`;
2. adding `CurriculumItem.pages`;
3. changing `CurriculumImporter` to return the complete import batch;
4. requiring institution and degree names at import time;
5. adding repository `update(entity)` for immutable entity replacement.

All five minimal amendments were approved. No additional domain concepts were
authorized by this checkpoint.
