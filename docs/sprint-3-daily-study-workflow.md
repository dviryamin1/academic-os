# Sprint 3 — Daily Study Workflow

Sprint 3 adds a local, rule-based workflow for deciding what to study without
introducing AI, scheduling, an API, or a permanent frontend.

## What was added

- Resume learning selects the item from the latest completed study session.
  When no completed session exists, it uses the latest
  `StudyProgress.status_updated_at`. With neither source, it returns no target.
- Next study recommendation prefers an open task on the resume item. Otherwise
  it selects the earliest open task by course and hierarchical curriculum
  order. Tasks on the same item use reading, summary, practice, then review
  priority.
- Open tasks excludes completed tasks and supports an exact course code or
  title filter.
- Course progress reports item status counts, task counts, and total completed
  study-session minutes.
- The temporary Streamlit UI exposes these workflows in a Today area above the
  existing hierarchical item workspace.

The domain amendment approved for this sprint adds only
`StudyProgress.status_updated_at`. Migration `0003` persists it and backfills
pre-existing progress rows with the migration time.

## CLI usage

Apply the latest migration first:

```powershell
uv run academic-os init-db
```

Then use:

```powershell
uv run academic-os resume
uv run academic-os next
uv run academic-os open-tasks
uv run academic-os open-tasks --course "סטטיסטיקה ב'"
uv run academic-os progress-summary
```

Launch the temporary local UI with:

```powershell
uv run streamlit run src\academic_os\interfaces\streamlit_app.py
```

## Known limitations

- Recommendations only consider study tasks that already exist.
- Course ordering is alphabetical by course title and code; there is no degree
  course sequence in the approved model.
- Progress is count-based and unweighted. An item without a progress row is
  counted as `not_started`.
- Study minutes include only sessions with an `ended_at` value.
- Timestamps remain naive local datetimes, consistent with the existing model.
- Existing progress rows receive the migration time as their initial
  `status_updated_at`; their historical update time was not previously stored.
- Streamlit remains a temporary local validation interface.

## Recommended next step

Evaluate these rules during real study sessions before expanding the model or
starting a permanent frontend. In particular, validate whether alphabetical
course ordering is sufficient for cross-course recommendations.
