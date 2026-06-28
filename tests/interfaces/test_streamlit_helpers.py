from datetime import datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from academic_os.interfaces.streamlit_app import _session_duration_minutes


def test_session_duration_minutes_handles_completed_and_open_sessions() -> None:
    started_at = datetime(2026, 11, 15, 11, 30)

    assert (
        _session_duration_minutes(
            started_at,
            datetime(2026, 11, 15, 12, 0),
        )
        == 30
    )
    assert _session_duration_minutes(started_at, None) == 0


def test_streamlit_app_starts_before_database_initialization(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "uninitialized.db"
    monkeypatch.setenv(
        "ACADEMIC_OS_DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    app_path = (
        Path(__file__).parents[2]
        / "src"
        / "academic_os"
        / "interfaces"
        / "streamlit_app.py"
    )

    app = AppTest.from_file(str(app_path)).run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "Academic OS"
    assert "Initialize the database" in app.info[0].value
