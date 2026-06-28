from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from academic_os.domain import (
    AcademicYear,
    Course,
    CurriculumItem,
    CurriculumItemType,
    Degree,
    DegreeCourse,
    Institution,
    Semester,
    StudyPlan,
    StudyPlanItem,
    StudyProgress,
    StudyProgressStatus,
    StudyTask,
    StudyTaskType,
)


class DomainModelTests(TestCase):
    def test_academic_calendar_has_explicit_year_hierarchy(self) -> None:
        institution = Institution(id=uuid4(), name="University")
        degree = Degree(
            id=uuid4(),
            institution_id=institution.id,
            name="Psychology",
        )
        academic_year = AcademicYear(
            id=uuid4(),
            degree_id=degree.id,
            label="2026/27",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 9, 30),
        )
        semester = Semester(
            id=uuid4(),
            academic_year_id=academic_year.id,
            name="Autumn",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 1, 31),
        )

        self.assertEqual(degree.institution_id, institution.id)
        self.assertEqual(academic_year.degree_id, degree.id)
        self.assertEqual(semester.academic_year_id, academic_year.id)

    def test_course_catalog_is_separate_from_degree_membership(self) -> None:
        institution_id = uuid4()
        degree_id = uuid4()
        course = Course(
            id=uuid4(),
            institution_id=institution_id,
            code="PSY-101",
            title="Introduction to Psychology",
        )
        degree_course = DegreeCourse(
            id=uuid4(),
            degree_id=degree_id,
            course_id=course.id,
            credits=Decimal("6"),
        )

        self.assertFalse(hasattr(course, "degree_id"))
        self.assertEqual(degree_course.course_id, course.id)
        self.assertEqual(degree_course.degree_id, degree_id)

    def test_curriculum_items_support_arbitrary_hierarchy_depth(self) -> None:
        course_id = uuid4()
        parent_id = None

        for order in range(100):
            item = CurriculumItem(
                id=uuid4(),
                code=f"TOPIC-{order}",
                parent_id=parent_id,
                title=f"Level {order}",
                item_type=CurriculumItemType(CurriculumItemType.TOPIC),
                course_id=course_id,
                source=None,
                pages=None,
                order=order,
            )
            parent_id = item.id

        self.assertIsNotNone(parent_id)

    def test_study_plan_is_separate_from_its_curriculum_entries(self) -> None:
        plan = StudyPlan(id=uuid4(), semester_id=uuid4())
        curriculum_item_id = uuid4()
        plan_item = StudyPlanItem(
            id=uuid4(),
            study_plan_id=plan.id,
            curriculum_item_id=curriculum_item_id,
        )

        self.assertFalse(hasattr(plan, "curriculum_item_id"))
        self.assertEqual(plan_item.study_plan_id, plan.id)
        self.assertEqual(plan_item.curriculum_item_id, curriculum_item_id)
        self.assertFalse(hasattr(plan_item, "curriculum_title"))

    def test_progress_is_independent_from_task_completion(self) -> None:
        curriculum_item_id = uuid4()
        progress = StudyProgress(
            id=uuid4(),
            curriculum_item_id=curriculum_item_id,
            status=StudyProgressStatus(StudyProgressStatus.IN_PROGRESS),
        )
        task = StudyTask(
            id=uuid4(),
            curriculum_item_id=curriculum_item_id,
            task_type=StudyTaskType(StudyTaskType.READING),
            title="Read chapter",
            due_at=None,
            completed_at=None,
        )

        self.assertEqual(progress.curriculum_item_id, task.curriculum_item_id)
        self.assertEqual(progress.status.code, "in_progress")
        self.assertEqual(task.task_type.code, "reading")

    def test_entities_and_value_objects_are_immutable(self) -> None:
        degree = Degree(
            id=uuid4(),
            institution_id=uuid4(),
            name="Psychology",
        )
        item_type = CurriculumItemType("chapter")

        with self.assertRaises(FrozenInstanceError):
            degree.name = "Changed"  # type: ignore[misc]

        with self.assertRaises(FrozenInstanceError):
            item_type.code = "unit"  # type: ignore[misc]
