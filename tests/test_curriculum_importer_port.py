from uuid import uuid4

from academic_os.application.ports import (
    CurriculumImporter,
    CurriculumImportResult,
)
from academic_os.domain import (
    Course,
    CurriculumItem,
    CurriculumItemType,
    Degree,
    Institution,
)


class TextCurriculumImporter:
    def import_curriculum(
        self,
        source: str,
        *,
        institution_name: str,
        degree_name: str,
    ) -> CurriculumImportResult:
        institution = Institution(id=uuid4(), name=institution_name)
        degree = Degree(
            id=uuid4(),
            institution_id=institution.id,
            name=degree_name,
        )
        course = Course(
            id=uuid4(),
            institution_id=institution.id,
            code="TEXT",
            title="Text course",
        )
        item = CurriculumItem(
            id=uuid4(),
            code="TEXT-1",
            parent_id=None,
            title=source,
            item_type=CurriculumItemType("root"),
            course_id=course.id,
            source=None,
            pages=None,
            order=0,
        )
        return CurriculumImportResult(
            institution=institution,
            degree=degree,
            courses=(course,),
            curriculum_items=(item,),
        )


def accepts_text_importer(
    importer: CurriculumImporter[str],
) -> CurriculumImportResult:
    return importer.import_curriculum(
        "Curriculum",
        institution_name="University",
        degree_name="Degree",
    )


def test_importer_port_is_format_agnostic() -> None:
    result = accepts_text_importer(TextCurriculumImporter())

    assert result.institution.name == "University"
    assert result.degree.name == "Degree"
    assert result.curriculum_items[0].title == "Curriculum"
