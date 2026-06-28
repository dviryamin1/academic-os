from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from academic_os.infrastructure.persistence.sqlalchemy.database import (
    create_database_engine,
)
from academic_os.infrastructure.persistence.sqlalchemy.models import Base


def test_initial_migration_matches_orm_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("ACADEMIC_OS_DATABASE_URL", database_url)

    configuration = Config("alembic.ini")
    command.upgrade(configuration, "head")
    command.check(configuration)

    engine = create_database_engine(database_url)
    try:
        migrated_tables = set(inspect(engine).get_table_names())
        expected_tables = set(Base.metadata.tables)

        assert migrated_tables == expected_tables | {"alembic_version"}
    finally:
        engine.dispose()

    command.downgrade(configuration, "base")

    engine = create_database_engine(database_url)
    try:
        remaining_tables = set(inspect(engine).get_table_names())
        assert remaining_tables <= {"alembic_version"}
    finally:
        engine.dispose()
