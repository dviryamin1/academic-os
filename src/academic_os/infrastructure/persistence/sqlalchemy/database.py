import os
from collections.abc import Callable
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENVIRONMENT_VARIABLE = "ACADEMIC_OS_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///academic_os.db"

SessionFactory = Callable[[], Session]


def get_database_url() -> str:
    return os.getenv(DATABASE_URL_ENVIRONMENT_VARIABLE, DEFAULT_DATABASE_URL)


def create_database_engine(
    database_url: str | None = None,
    *,
    echo: bool = False,
) -> Engine:
    url = database_url or get_database_url()
    engine = create_engine(url, echo=echo)

    if engine.dialect.name == "sqlite":
        _enable_sqlite_foreign_keys(engine)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_foreign_keys(database_connection: Any, _: Any) -> None:
        cursor = database_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
