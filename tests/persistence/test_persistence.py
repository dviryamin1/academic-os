from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from academic_os.domain import (
    AcademicYear,
    Assignment,
    Course,
    CurriculumItem,
    CurriculumItemType,
    Degree,
    DegreeCourse,
    Event,
    Exam,
    Institution,
    Note,
    Semester,
    StudyPlan,
    StudyPlanItem,
    StudyProgress,
    StudyProgressStatus,
    StudySession,
    StudyTask,
    StudyTaskType,
)
from academic_os.infrastructure.persistence.sqlalchemy.database import SessionFactory
from academic_os.infrastructure.persistence.sqlalchemy.models import (
    CourseModel,
    CurriculumItemModel,
    StudyPlanModel,
)
from academic_os.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def test_complete_domain_graph_can_be_persisted(
    session_factory: SessionFactory,
) -> None:
    institution = Institution(id=uuid4(), name="Open University")
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
        name="A",
        start_date=date(2026, 10, 1),
        end_date=date(2027, 1, 31),
    )
    course = Course(
        id=uuid4(),
        institution_id=institution.id,
        code="PSY-101",
        title="Introduction to Psychology",
    )
    degree_course = DegreeCourse(
        id=uuid4(),
        degree_id=degree.id,
        course_id=course.id,
        credits=Decimal("6.00"),
    )
    chapter = CurriculumItem(
        id=uuid4(),
        parent_id=None,
        title="Foundations",
        item_type=CurriculumItemType(CurriculumItemType.CHAPTER),
        course_id=course.id,
        source="Textbook",
        order=1,
    )
    topic = CurriculumItem(
        id=uuid4(),
        parent_id=chapter.id,
        title="Scientific method",
        item_type=CurriculumItemType(CurriculumItemType.TOPIC),
        course_id=course.id,
        source=None,
        order=1,
    )
    study_plan = StudyPlan(id=uuid4(), semester_id=semester.id)
    study_plan_item = StudyPlanItem(
        id=uuid4(),
        study_plan_id=study_plan.id,
        curriculum_item_id=topic.id,
    )
    task = StudyTask(
        id=uuid4(),
        curriculum_item_id=topic.id,
        task_type=StudyTaskType(StudyTaskType.READING),
        title="Read the topic",
        due_at=datetime(2026, 11, 1, 18, 0),
        completed_at=None,
    )
    study_session = StudySession(
        id=uuid4(),
        curriculum_item_id=topic.id,
        started_at=datetime(2026, 10, 20, 10, 0),
        ended_at=datetime(2026, 10, 20, 11, 0),
    )
    progress = StudyProgress(
        id=uuid4(),
        curriculum_item_id=topic.id,
        status=StudyProgressStatus(StudyProgressStatus.IN_PROGRESS),
    )
    event = Event(
        id=uuid4(),
        title="University orientation",
        starts_at=datetime(2026, 10, 1, 9, 0),
        ends_at=None,
    )
    note = Note(
        id=uuid4(),
        curriculum_item_id=topic.id,
        content="Science relies on empirical evidence.",
        created_at=datetime(2026, 10, 20, 11, 5),
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Assignment 1",
        due_at=datetime(2026, 12, 1, 23, 59),
    )
    exam = Exam(
        id=uuid4(),
        course_id=course.id,
        title="Final exam",
        starts_at=datetime(2027, 2, 10, 9, 0),
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.institutions.add(institution)
        unit_of_work.degrees.add(degree)
        unit_of_work.academic_years.add(academic_year)
        unit_of_work.semesters.add(semester)
        unit_of_work.courses.add(course)
        unit_of_work.degree_courses.add(degree_course)
        unit_of_work.curriculum_items.add(chapter)
        unit_of_work.curriculum_items.add(topic)
        unit_of_work.study_plans.add(study_plan)
        unit_of_work.study_plan_items.add(study_plan_item)
        unit_of_work.study_tasks.add(task)
        unit_of_work.study_sessions.add(study_session)
        unit_of_work.study_progress.add(progress)
        unit_of_work.events.add(event)
        unit_of_work.notes.add(note)
        unit_of_work.assignments.add(assignment)
        unit_of_work.exams.add(exam)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.institutions.get(institution.id) == institution
        assert unit_of_work.degrees.get(degree.id) == degree
        assert unit_of_work.academic_years.get(academic_year.id) == academic_year
        assert unit_of_work.semesters.get(semester.id) == semester
        assert unit_of_work.courses.get(course.id) == course
        assert unit_of_work.degree_courses.get(degree_course.id) == degree_course
        assert unit_of_work.curriculum_items.get(chapter.id) == chapter
        assert unit_of_work.curriculum_items.get(topic.id) == topic
        assert unit_of_work.study_plans.get(study_plan.id) == study_plan
        assert (
            unit_of_work.study_plan_items.get(study_plan_item.id)
            == study_plan_item
        )
        assert unit_of_work.study_tasks.get(task.id) == task
        assert unit_of_work.study_sessions.get(study_session.id) == study_session
        assert unit_of_work.study_progress.get(progress.id) == progress
        assert unit_of_work.events.get(event.id) == event
        assert unit_of_work.notes.get(note.id) == note
        assert unit_of_work.assignments.get(assignment.id) == assignment
        assert unit_of_work.exams.get(exam.id) == exam

    _assert_orm_relationships(
        session_factory,
        course_id=course.id,
        chapter_id=chapter.id,
        topic_id=topic.id,
        study_plan_id=study_plan.id,
    )


def test_repository_lists_and_removes_entities(
    session_factory: SessionFactory,
) -> None:
    first = Institution(id=uuid4(), name="First University")
    second = Institution(id=uuid4(), name="Second University")

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.institutions.add(first)
        unit_of_work.institutions.add(second)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert set(unit_of_work.institutions.list_all()) == {first, second}
        assert unit_of_work.institutions.remove(first.id) is True
        assert unit_of_work.institutions.remove(uuid4()) is False
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.institutions.get(first.id) is None
        assert unit_of_work.institutions.get(second.id) == second


def test_uncommitted_unit_of_work_is_rolled_back(
    session_factory: SessionFactory,
) -> None:
    institution = Institution(id=uuid4(), name="Rolled Back University")

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.institutions.add(institution)

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.institutions.get(institution.id) is None


def _assert_orm_relationships(
    session_factory: SessionFactory,
    *,
    course_id,
    chapter_id,
    topic_id,
    study_plan_id,
) -> None:
    with session_factory() as session:
        course = session.get(CourseModel, course_id)
        chapter = session.get(CurriculumItemModel, chapter_id)
        topic = session.get(CurriculumItemModel, topic_id)
        study_plan = session.get(StudyPlanModel, study_plan_id)

        assert course is not None
        assert chapter is not None
        assert topic is not None
        assert study_plan is not None
        assert {item.id for item in chapter.children} == {topic_id}
        assert topic.parent is chapter
        assert len(course.degree_courses) == 1
        assert len(course.assignments) == 1
        assert len(course.exams) == 1
        assert len(study_plan.items) == 1

