from collections.abc import Iterable
from unittest import TestCase
from uuid import uuid4

from academic_os.application.ports import CurriculumImporter
from academic_os.domain import CurriculumItem, CurriculumItemType


class TextCurriculumImporter:
    def import_curriculum(self, source: str) -> Iterable[CurriculumItem]:
        yield CurriculumItem(
            id=uuid4(),
            parent_id=None,
            title=source,
            item_type=CurriculumItemType("root"),
            course_id=uuid4(),
            source=None,
            order=0,
        )


def accepts_text_importer(importer: CurriculumImporter[str]) -> None:
    list(importer.import_curriculum("Curriculum"))


class CurriculumImporterPortTests(TestCase):
    def test_importer_port_is_format_agnostic(self) -> None:
        accepts_text_importer(TextCurriculumImporter())
