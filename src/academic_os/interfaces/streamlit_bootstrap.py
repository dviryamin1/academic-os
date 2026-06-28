from academic_os.application.services import WorkspaceService
from academic_os.infrastructure.importers import JsonCurriculumImporter
from academic_os.infrastructure.persistence.sqlalchemy import (
    SqlAlchemyUnitOfWork,
    create_database_engine,
    create_session_factory,
    get_database_url,
    upgrade_database,
)


def build_workspace_service(database_url: str) -> WorkspaceService:
    """Compose the temporary GUI's application service dependencies."""

    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    return WorkspaceService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        JsonCurriculumImporter(),
        database_initializer=lambda: upgrade_database(database_url),
    )


def default_database_url() -> str:
    return get_database_url()
