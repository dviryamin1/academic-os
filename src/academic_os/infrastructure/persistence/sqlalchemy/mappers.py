from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

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
from academic_os.infrastructure.persistence.sqlalchemy.models import (
    AcademicYearModel,
    AssignmentModel,
    Base,
    CourseModel,
    CurriculumItemModel,
    DegreeCourseModel,
    DegreeModel,
    EventModel,
    ExamModel,
    InstitutionModel,
    NoteModel,
    SemesterModel,
    StudyPlanItemModel,
    StudyPlanModel,
    StudyProgressModel,
    StudySessionModel,
    StudyTaskModel,
)

DomainT = TypeVar("DomainT")
ModelT = TypeVar("ModelT", bound=Base)


@dataclass(frozen=True, slots=True)
class EntityMapper(Generic[DomainT, ModelT]):
    model_type: type[ModelT]
    to_model: Callable[[DomainT], ModelT]
    to_domain: Callable[[ModelT], DomainT]


INSTITUTION_MAPPER = EntityMapper(
    model_type=InstitutionModel,
    to_model=lambda entity: InstitutionModel(id=entity.id, name=entity.name),
    to_domain=lambda model: Institution(id=model.id, name=model.name),
)

DEGREE_MAPPER = EntityMapper(
    model_type=DegreeModel,
    to_model=lambda entity: DegreeModel(
        id=entity.id,
        institution_id=entity.institution_id,
        name=entity.name,
    ),
    to_domain=lambda model: Degree(
        id=model.id,
        institution_id=model.institution_id,
        name=model.name,
    ),
)

ACADEMIC_YEAR_MAPPER = EntityMapper(
    model_type=AcademicYearModel,
    to_model=lambda entity: AcademicYearModel(
        id=entity.id,
        degree_id=entity.degree_id,
        label=entity.label,
        start_date=entity.start_date,
        end_date=entity.end_date,
    ),
    to_domain=lambda model: AcademicYear(
        id=model.id,
        degree_id=model.degree_id,
        label=model.label,
        start_date=model.start_date,
        end_date=model.end_date,
    ),
)

SEMESTER_MAPPER = EntityMapper(
    model_type=SemesterModel,
    to_model=lambda entity: SemesterModel(
        id=entity.id,
        academic_year_id=entity.academic_year_id,
        name=entity.name,
        start_date=entity.start_date,
        end_date=entity.end_date,
    ),
    to_domain=lambda model: Semester(
        id=model.id,
        academic_year_id=model.academic_year_id,
        name=model.name,
        start_date=model.start_date,
        end_date=model.end_date,
    ),
)

COURSE_MAPPER = EntityMapper(
    model_type=CourseModel,
    to_model=lambda entity: CourseModel(
        id=entity.id,
        institution_id=entity.institution_id,
        code=entity.code,
        title=entity.title,
    ),
    to_domain=lambda model: Course(
        id=model.id,
        institution_id=model.institution_id,
        code=model.code,
        title=model.title,
    ),
)

DEGREE_COURSE_MAPPER = EntityMapper(
    model_type=DegreeCourseModel,
    to_model=lambda entity: DegreeCourseModel(
        id=entity.id,
        degree_id=entity.degree_id,
        course_id=entity.course_id,
        credits=entity.credits,
    ),
    to_domain=lambda model: DegreeCourse(
        id=model.id,
        degree_id=model.degree_id,
        course_id=model.course_id,
        credits=model.credits,
    ),
)

CURRICULUM_ITEM_MAPPER = EntityMapper(
    model_type=CurriculumItemModel,
    to_model=lambda entity: CurriculumItemModel(
        id=entity.id,
        code=entity.code,
        parent_id=entity.parent_id,
        title=entity.title,
        item_type=entity.item_type.code,
        course_id=entity.course_id,
        source=entity.source,
        pages=entity.pages,
        order=entity.order,
    ),
    to_domain=lambda model: CurriculumItem(
        id=model.id,
        code=model.code,
        parent_id=model.parent_id,
        title=model.title,
        item_type=CurriculumItemType(model.item_type),
        course_id=model.course_id,
        source=model.source,
        pages=model.pages,
        order=model.order,
    ),
)

STUDY_PLAN_MAPPER = EntityMapper(
    model_type=StudyPlanModel,
    to_model=lambda entity: StudyPlanModel(
        id=entity.id,
        semester_id=entity.semester_id,
    ),
    to_domain=lambda model: StudyPlan(
        id=model.id,
        semester_id=model.semester_id,
    ),
)

STUDY_PLAN_ITEM_MAPPER = EntityMapper(
    model_type=StudyPlanItemModel,
    to_model=lambda entity: StudyPlanItemModel(
        id=entity.id,
        study_plan_id=entity.study_plan_id,
        curriculum_item_id=entity.curriculum_item_id,
    ),
    to_domain=lambda model: StudyPlanItem(
        id=model.id,
        study_plan_id=model.study_plan_id,
        curriculum_item_id=model.curriculum_item_id,
    ),
)

STUDY_TASK_MAPPER = EntityMapper(
    model_type=StudyTaskModel,
    to_model=lambda entity: StudyTaskModel(
        id=entity.id,
        curriculum_item_id=entity.curriculum_item_id,
        task_type=entity.task_type.code,
        title=entity.title,
        due_at=entity.due_at,
        completed_at=entity.completed_at,
    ),
    to_domain=lambda model: StudyTask(
        id=model.id,
        curriculum_item_id=model.curriculum_item_id,
        task_type=StudyTaskType(model.task_type),
        title=model.title,
        due_at=model.due_at,
        completed_at=model.completed_at,
    ),
)

STUDY_SESSION_MAPPER = EntityMapper(
    model_type=StudySessionModel,
    to_model=lambda entity: StudySessionModel(
        id=entity.id,
        curriculum_item_id=entity.curriculum_item_id,
        started_at=entity.started_at,
        ended_at=entity.ended_at,
    ),
    to_domain=lambda model: StudySession(
        id=model.id,
        curriculum_item_id=model.curriculum_item_id,
        started_at=model.started_at,
        ended_at=model.ended_at,
    ),
)

STUDY_PROGRESS_MAPPER = EntityMapper(
    model_type=StudyProgressModel,
    to_model=lambda entity: StudyProgressModel(
        id=entity.id,
        curriculum_item_id=entity.curriculum_item_id,
        status=entity.status.code,
    ),
    to_domain=lambda model: StudyProgress(
        id=model.id,
        curriculum_item_id=model.curriculum_item_id,
        status=StudyProgressStatus(model.status),
    ),
)

EVENT_MAPPER = EntityMapper(
    model_type=EventModel,
    to_model=lambda entity: EventModel(
        id=entity.id,
        title=entity.title,
        starts_at=entity.starts_at,
        ends_at=entity.ends_at,
    ),
    to_domain=lambda model: Event(
        id=model.id,
        title=model.title,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
    ),
)

NOTE_MAPPER = EntityMapper(
    model_type=NoteModel,
    to_model=lambda entity: NoteModel(
        id=entity.id,
        curriculum_item_id=entity.curriculum_item_id,
        content=entity.content,
        created_at=entity.created_at,
    ),
    to_domain=lambda model: Note(
        id=model.id,
        curriculum_item_id=model.curriculum_item_id,
        content=model.content,
        created_at=model.created_at,
    ),
)

ASSIGNMENT_MAPPER = EntityMapper(
    model_type=AssignmentModel,
    to_model=lambda entity: AssignmentModel(
        id=entity.id,
        course_id=entity.course_id,
        title=entity.title,
        due_at=entity.due_at,
    ),
    to_domain=lambda model: Assignment(
        id=model.id,
        course_id=model.course_id,
        title=model.title,
        due_at=model.due_at,
    ),
)

EXAM_MAPPER = EntityMapper(
    model_type=ExamModel,
    to_model=lambda entity: ExamModel(
        id=entity.id,
        course_id=entity.course_id,
        title=entity.title,
        starts_at=entity.starts_at,
    ),
    to_domain=lambda model: Exam(
        id=model.id,
        course_id=model.course_id,
        title=model.title,
        starts_at=model.starts_at,
    ),
)
