"""Inbound and outbound application ports."""

from academic_os.application.ports.curriculum_importer import (
    CurriculumImporter,
    CurriculumImportResult,
)
from academic_os.application.ports.repositories import Repository
from academic_os.application.ports.unit_of_work import UnitOfWork

__all__ = [
    "CurriculumImporter",
    "CurriculumImportResult",
    "Repository",
    "UnitOfWork",
]
