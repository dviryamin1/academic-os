from collections.abc import Iterator

import pytest

from academic_os.infrastructure.persistence.sqlalchemy.database import (
    SessionFactory,
    create_database_engine,
    create_session_factory,
)
from academic_os.infrastructure.persistence.sqlalchemy.models import Base


@pytest.fixture
def session_factory(tmp_path) -> Iterator[SessionFactory]:
    database_path = tmp_path / "persistence-test.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)

    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()

