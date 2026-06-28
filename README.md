# Academic OS

Academic OS is a local-first academic workspace organized around curriculum
items.

## Local CLI setup

For complete fresh-Windows setup instructions using `uv`, see
[docs/windows-uv-setup.md](docs/windows-uv-setup.md).

From PowerShell in an existing clone:

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
uv run academic-os init-db
uv run academic-os import-curriculum .\course_catalog_hebrew_values.json
uv run academic-os list-courses
```

The import command defaults to:

- institution: `האוניברסיטה הפתוחה`
- degree: `פסיכולוגיה`

Override them when needed:

```powershell
academic-os import-curriculum .\curriculum.json `
  --institution-name "University" `
  --degree-name "Degree"
```

## Curriculum-item workflow

```powershell
academic-os list-items --course "סטטיסטיקה ב'"
academic-os show-item STAT-10.8
academic-os create-default-tasks STAT-10.8
academic-os complete-task TASK_UUID
academic-os add-note STAT-10.8 "הערה"
academic-os log-session STAT-10.8 --minutes 30
academic-os set-progress STAT-10.8 in_progress
```

Use `uv run academic-os --help` or
`uv run academic-os COMMAND --help` for command details.
