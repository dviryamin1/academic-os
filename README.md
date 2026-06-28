# Academic OS

Academic OS is a local-first academic workspace organized around curriculum
items. The current Streamlit interface is temporary and exists to validate the
study workflow before a permanent frontend is designed.

## Installation

For complete fresh-Windows instructions, see
[docs/windows-uv-setup.md](docs/windows-uv-setup.md).

From PowerShell in the cloned repository:

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
```

## Database initialization

Initialize or upgrade the local SQLite database:

```powershell
uv run academic-os init-db
```

The default database is `academic_os.db` in the project directory. Override it
with `ACADEMIC_OS_DATABASE_URL` or the CLI `--database-url` option.

## Curriculum import

Import the supplied catalog:

```powershell
uv run academic-os import-curriculum `
  .\course_catalog_hebrew_values.json
```

The default import context is:

- institution: `האוניברסיטה הפתוחה`
- degree: `פסיכולוגיה`

Override it when needed:

```powershell
uv run academic-os import-curriculum .\curriculum.json `
  --institution-name "University" `
  --degree-name "Degree"
```

## CLI usage

```powershell
uv run academic-os list-courses
uv run academic-os list-items --course "סטטיסטיקה ב'"
uv run academic-os show-item STAT-10.8
uv run academic-os create-default-tasks STAT-10.8
uv run academic-os complete-task TASK_UUID
uv run academic-os add-note STAT-10.8 "הערה"
uv run academic-os log-session STAT-10.8 --minutes 30
uv run academic-os set-progress STAT-10.8 in_progress
```

Use `uv run academic-os --help` for the complete command reference.

## Streamlit usage

Launch the temporary graphical workspace:

```powershell
uv run streamlit run src\academic_os\interfaces\streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) if the browser does not open
automatically.

From the interface:

1. Initialize the database from the sidebar.
2. Upload and import the curriculum JSON.
3. Select a course and curriculum item.
4. Work through tasks, notes, study history, and progress.

The Streamlit interface and CLI use the same Application Services and database.
The GUI does not access repositories directly.

## Dogfooding

Use [DOGFOODING.md](DOGFOODING.md) to evaluate Academic OS during real study
sessions and record structured observations.
