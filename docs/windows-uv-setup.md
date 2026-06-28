# Running Academic OS on a Fresh Windows Machine with uv

These instructions use Windows PowerShell.

## 1. Install Git and uv

Open PowerShell and run:

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

Close PowerShell, open a new PowerShell window, and verify both commands:

```powershell
git --version
uv --version
```

If `winget` is unavailable, install uv with its official PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then open a new PowerShell window and run `uv --version` again.

## 2. Clone Academic OS

```powershell
Set-Location $HOME
git clone https://github.com/dviryamin1/academic-os.git
Set-Location .\academic-os
```

Confirm that this is the project root:

```powershell
Get-Item .\pyproject.toml
```

## 3. Install Python and project dependencies

```powershell
uv python install 3.12
uv venv --python 3.12
uv sync
```

`uv sync` installs Academic OS and its runtime dependencies into `.venv`.

## 4. Place the curriculum JSON

Check whether the file is already present:

```powershell
Test-Path .\course_catalog_hebrew_values.json
```

If the result is `False`, copy the supplied file into the repository root.
Replace the source path below with the file's actual location:

```powershell
Copy-Item "C:\FULL\PATH\TO\course_catalog_hebrew_values.json" `
  ".\course_catalog_hebrew_values.json"
```

Verify it:

```powershell
Get-Item .\course_catalog_hebrew_values.json
```

## 5. Initialize, import, and list courses

The recommended approach does not require activating `.venv`:

```powershell
uv run academic-os init-db
uv run academic-os import-curriculum .\course_catalog_hebrew_values.json
uv run academic-os list-courses
```

The final command should list three courses from the supplied catalog.

## Running `academic-os` directly

Activate the project environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then the direct command is available:

```powershell
academic-os list-courses
```

When finished:

```powershell
deactivate
```

If PowerShell blocks the activation script, allow scripts only for the current
PowerShell process and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
academic-os list-courses
```

## If `academic-os` is not available directly

Use the project command through uv:

```powershell
uv run academic-os list-courses
```

Or invoke the executable inside `.venv` explicitly:

```powershell
.\.venv\Scripts\academic-os.exe list-courses
```

The module entry point is the final fallback:

```powershell
uv run python -m academic_os.interfaces.cli list-courses
```

All commands must be run from the cloned `academic-os` directory unless a
database URL and migration configuration are supplied explicitly.

