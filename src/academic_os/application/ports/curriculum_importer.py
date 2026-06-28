from dataclasses import dataclass
from typing import Protocol, TypeVar

from academic_os.domain import Course, CurriculumItem, Degree, Institution

SourceT = TypeVar("SourceT", contravariant=True)


@dataclass(frozen=True, slots=True)
class CurriculumImportResult:
    """Complete domain graph produced by curriculum source mapping."""

    institution: Institution
    degree: Degree
    courses: tuple[Course, ...]
    curriculum_items: tuple[CurriculumItem, ...]


class CurriculumImporter(Protocol[SourceT]):
    """Maps an external curriculum source without persisting it."""

    def import_curriculum(
        self,
        source: SourceT,
        *,
        institution_name: str,
        degree_name: str,
    ) -> CurriculumImportResult:
        ...

