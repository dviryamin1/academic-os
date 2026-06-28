# Academic OS

Academic OS is a local-first academic workspace organized around curriculum
items.

## Local CLI setup

From PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
academic-os init-db
academic-os import-curriculum .\course_catalog_hebrew_values.json
academic-os list-courses
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

Use `academic-os --help` or `academic-os COMMAND --help` for command details.

