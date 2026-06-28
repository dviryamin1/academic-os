from pathlib import Path

from alembic import command
from alembic.config import Config

DEFAULT_ALEMBIC_CONFIGURATION = (
    Path(__file__).resolve().parents[5] / "alembic.ini"
)


def upgrade_database(
    database_url: str,
    *,
    configuration_path: Path = DEFAULT_ALEMBIC_CONFIGURATION,
) -> None:
    if not configuration_path.is_file():
        raise FileNotFoundError(
            f"Alembic configuration was not found: {configuration_path}"
        )

    configuration = Config(str(configuration_path))
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "head")
