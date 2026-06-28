from collections.abc import Iterable
from typing import Protocol, TypeVar

from academic_os.domain import CurriculumItem

SourceT = TypeVar("SourceT", contravariant=True)


class CurriculumImporter(Protocol[SourceT]):
    """Converts an external curriculum source into domain entities."""

    def import_curriculum(self, source: SourceT) -> Iterable[CurriculumItem]:
        ...

