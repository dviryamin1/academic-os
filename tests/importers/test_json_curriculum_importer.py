import json

from academic_os.infrastructure.importers.json_curriculum_importer import (
    JsonCurriculumImporter,
)


def test_json_import_preserves_hebrew_values_and_hierarchy(tmp_path) -> None:
    source = tmp_path / "curriculum.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "items": [
                    {
                        "id": "STAT-10",
                        "parent_id": None,
                        "level": 1,
                        "type": "unit",
                        "course": "סטטיסטיקה ב'",
                        "source": "יחידה 10",
                        "part": None,
                        "title": "רווחי סמך",
                        "pages": "1-20",
                    },
                    {
                        "id": "STAT-10.8",
                        "parent_id": "STAT-10",
                        "level": 2,
                        "type": "subtopic",
                        "course": "סטטיסטיקה ב'",
                        "source": "יחידה 10",
                        "part": None,
                        "title": "בדיקת השערות",
                        "pages": "21-35",
                    },
                    {
                        "id": "AGE-A01",
                        "parent_id": None,
                        "level": 1,
                        "type": "article",
                        "course": "פסיכולוגיה של הזדקנות",
                        "source": "מקראה",
                        "part": None,
                        "title": "Successful Ageing",
                        "pages": "100-120",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = JsonCurriculumImporter().import_curriculum(
        source,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )

    assert result.institution.name == "האוניברסיטה הפתוחה"
    assert result.degree.name == "פסיכולוגיה"
    assert [course.title for course in result.courses] == [
        "סטטיסטיקה ב'",
        "פסיכולוגיה של הזדקנות",
    ]
    assert [course.code for course in result.courses] == ["STAT", "AGE"]

    parent = next(
        item for item in result.curriculum_items if item.code == "STAT-10"
    )
    child = next(
        item for item in result.curriculum_items if item.code == "STAT-10.8"
    )
    assert child.parent_id == parent.id
    assert child.title == "בדיקת השערות"
    assert child.source == "יחידה 10"
    assert child.pages == "21-35"


def test_json_import_is_deterministic(tmp_path) -> None:
    source = tmp_path / "curriculum.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "DP-01",
                        "parent_id": None,
                        "type": "chapter",
                        "course": "פסיכולוגיה התפתחותית",
                        "source": "כרך א",
                        "title": "מבוא",
                        "pages": "1-10",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    importer = JsonCurriculumImporter()

    first = importer.import_curriculum(
        source,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )
    second = importer.import_curriculum(
        source,
        institution_name="האוניברסיטה הפתוחה",
        degree_name="פסיכולוגיה",
    )

    assert first == second

