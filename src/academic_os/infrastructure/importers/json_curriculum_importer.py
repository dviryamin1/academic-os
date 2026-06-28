import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from academic_os.application.ports import CurriculumImportResult
from academic_os.domain import (
    Course,
    CurriculumItem,
    CurriculumItemType,
    Degree,
    Institution,
)

IMPORT_NAMESPACE = uuid5(NAMESPACE_URL, "academic-os:curriculum-import:v1")


class CurriculumImportError(ValueError):
    """The external curriculum source cannot be mapped safely."""


class JsonCurriculumImporter:
    """Maps the supported JSON curriculum format into domain entities."""

    def import_curriculum(
        self,
        source: Path,
        *,
        institution_name: str,
        degree_name: str,
    ) -> CurriculumImportResult:
        if not institution_name.strip():
            raise CurriculumImportError("Institution name cannot be empty")
        if not degree_name.strip():
            raise CurriculumImportError("Degree name cannot be empty")

        records = self._read_records(source)
        institution = Institution(
            id=_stable_uuid("institution", institution_name),
            name=institution_name,
        )
        degree = Degree(
            id=_stable_uuid("degree", str(institution.id), degree_name),
            institution_id=institution.id,
            name=degree_name,
        )
        courses = self._map_courses(records, institution.id)
        course_by_name = {course.title: course for course in courses}
        curriculum_items = self._map_items(records, course_by_name)

        return CurriculumImportResult(
            institution=institution,
            degree=degree,
            courses=tuple(courses),
            curriculum_items=tuple(curriculum_items),
        )

    def _read_records(self, source: Path) -> list[dict[str, Any]]:
        try:
            raw_data = json.loads(source.read_text(encoding="utf-8-sig"))
        except OSError as error:
            raise CurriculumImportError(
                f"Cannot read curriculum file: {source}"
            ) from error
        except json.JSONDecodeError as error:
            raise CurriculumImportError(
                f"Invalid JSON at line {error.lineno}, column {error.colno}"
            ) from error

        if not isinstance(raw_data, dict) or not isinstance(
            raw_data.get("items"),
            list,
        ):
            raise CurriculumImportError(
                "Curriculum JSON must contain an 'items' array"
            )

        records = raw_data["items"]
        if not records:
            raise CurriculumImportError("Curriculum JSON contains no items")
        if not all(isinstance(record, dict) for record in records):
            raise CurriculumImportError(
                "Every curriculum item must be a JSON object"
            )
        return records

    def _map_courses(
        self,
        records: list[dict[str, Any]],
        institution_id: UUID,
    ) -> list[Course]:
        course_names: list[str] = []
        records_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for record in records:
            course_name = _required_string(record, "course")
            if course_name not in records_by_course:
                course_names.append(course_name)
            records_by_course[course_name].append(record)

        courses: list[Course] = []
        used_codes: set[str] = set()
        for course_name in course_names:
            course_id = _stable_uuid(
                "course",
                str(institution_id),
                course_name,
            )
            course_code = _derive_course_code(
                records_by_course[course_name],
                course_id,
            )
            if course_code in used_codes:
                course_code = f"{course_code}-{course_id.hex[:6].upper()}"
            used_codes.add(course_code)
            courses.append(
                Course(
                    id=course_id,
                    institution_id=institution_id,
                    code=course_code,
                    title=course_name,
                )
            )

        return courses

    def _map_items(
        self,
        records: list[dict[str, Any]],
        course_by_name: dict[str, Course],
    ) -> list[CurriculumItem]:
        item_ids: dict[tuple[str, str], UUID] = {}
        for record in records:
            course_name = _required_string(record, "course")
            item_code = _required_string(record, "id")
            key = (course_name, item_code)
            if key in item_ids:
                raise CurriculumImportError(
                    f"Duplicate curriculum item code: {item_code}"
                )
            item_ids[key] = _stable_uuid(
                "curriculum-item",
                str(course_by_name[course_name].id),
                item_code,
            )

        sibling_orders: dict[tuple[str, str | None], int] = defaultdict(int)
        items: list[CurriculumItem] = []
        for record in records:
            course_name = _required_string(record, "course")
            item_code = _required_string(record, "id")
            parent_code = _optional_string(record, "parent_id")
            parent_id = None
            if parent_code is not None:
                parent_id = item_ids.get((course_name, parent_code))
                if parent_id is None:
                    raise CurriculumImportError(
                        f"Unknown parent '{parent_code}' for '{item_code}'"
                    )

            order_key = (course_name, parent_code)
            order = sibling_orders[order_key]
            sibling_orders[order_key] += 1
            course = course_by_name[course_name]
            items.append(
                CurriculumItem(
                    id=item_ids[(course_name, item_code)],
                    code=item_code,
                    parent_id=parent_id,
                    title=_required_string(record, "title"),
                    item_type=CurriculumItemType(
                        _required_string(record, "type")
                    ),
                    course_id=course.id,
                    source=_optional_string(record, "source"),
                    pages=_optional_string(record, "pages"),
                    order=order,
                )
            )

        return items


def _required_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        item_reference = record.get("id", "<unknown>")
        raise CurriculumImportError(
            f"Item '{item_reference}' requires a non-empty '{key}'"
        )
    return value


def _optional_string(record: dict[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        item_reference = record.get("id", "<unknown>")
        raise CurriculumImportError(
            f"Item '{item_reference}' has a non-string '{key}'"
        )
    return value


def _derive_course_code(
    records: list[dict[str, Any]],
    course_id: UUID,
) -> str:
    prefixes = {
        item_code.split("-", maxsplit=1)[0]
        for record in records
        if "-" in (item_code := _required_string(record, "id"))
    }
    if len(prefixes) == 1:
        return prefixes.pop()
    return f"COURSE-{course_id.hex[:8].upper()}"


def _stable_uuid(kind: str, *parts: str) -> UUID:
    value = ":".join((kind, *parts))
    return uuid5(IMPORT_NAMESPACE, value)
