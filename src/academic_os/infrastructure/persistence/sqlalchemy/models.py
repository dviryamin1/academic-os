from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class InstitutionModel(Base):
    __tablename__ = "institutions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    degrees: Mapped[list[DegreeModel]] = relationship(back_populates="institution")
    courses: Mapped[list[CourseModel]] = relationship(back_populates="institution")


class DegreeModel(Base):
    __tablename__ = "degrees"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String)

    institution: Mapped[InstitutionModel] = relationship(back_populates="degrees")
    academic_years: Mapped[list[AcademicYearModel]] = relationship(
        back_populates="degree"
    )
    degree_courses: Mapped[list[DegreeCourseModel]] = relationship(
        back_populates="degree"
    )


class AcademicYearModel(Base):
    __tablename__ = "academic_years"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    degree_id: Mapped[UUID] = mapped_column(ForeignKey("degrees.id"), index=True)
    label: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    degree: Mapped[DegreeModel] = relationship(back_populates="academic_years")
    semesters: Mapped[list[SemesterModel]] = relationship(
        back_populates="academic_year"
    )


class SemesterModel(Base):
    __tablename__ = "semesters"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    academic_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_years.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    academic_year: Mapped[AcademicYearModel] = relationship(
        back_populates="semesters"
    )
    study_plans: Mapped[list[StudyPlanModel]] = relationship(
        back_populates="semester"
    )


class CourseModel(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)

    institution: Mapped[InstitutionModel] = relationship(back_populates="courses")
    degree_courses: Mapped[list[DegreeCourseModel]] = relationship(
        back_populates="course"
    )
    curriculum_items: Mapped[list[CurriculumItemModel]] = relationship(
        back_populates="course"
    )
    assignments: Mapped[list[AssignmentModel]] = relationship(
        back_populates="course"
    )
    exams: Mapped[list[ExamModel]] = relationship(back_populates="course")


class DegreeCourseModel(Base):
    __tablename__ = "degree_courses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    degree_id: Mapped[UUID] = mapped_column(ForeignKey("degrees.id"), index=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    credits: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    degree: Mapped[DegreeModel] = relationship(back_populates="degree_courses")
    course: Mapped[CourseModel] = relationship(back_populates="degree_courses")


class CurriculumItemModel(Base):
    __tablename__ = "curriculum_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    code: Mapped[str] = mapped_column(String)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("curriculum_items.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String)
    item_type: Mapped[str] = mapped_column(String)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages: Mapped[str | None] = mapped_column(String, nullable=True)
    order: Mapped[int] = mapped_column()

    parent: Mapped[CurriculumItemModel | None] = relationship(
        back_populates="children",
        remote_side="CurriculumItemModel.id",
    )
    children: Mapped[list[CurriculumItemModel]] = relationship(
        back_populates="parent"
    )
    course: Mapped[CourseModel] = relationship(back_populates="curriculum_items")
    study_plan_items: Mapped[list[StudyPlanItemModel]] = relationship(
        back_populates="curriculum_item"
    )
    study_tasks: Mapped[list[StudyTaskModel]] = relationship(
        back_populates="curriculum_item"
    )
    study_sessions: Mapped[list[StudySessionModel]] = relationship(
        back_populates="curriculum_item"
    )
    study_progress: Mapped[StudyProgressModel | None] = relationship(
        back_populates="curriculum_item"
    )
    notes: Mapped[list[NoteModel]] = relationship(
        back_populates="curriculum_item"
    )


class StudyPlanModel(Base):
    __tablename__ = "study_plans"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    semester_id: Mapped[UUID] = mapped_column(
        ForeignKey("semesters.id"),
        index=True,
    )

    semester: Mapped[SemesterModel] = relationship(back_populates="study_plans")
    items: Mapped[list[StudyPlanItemModel]] = relationship(
        back_populates="study_plan"
    )


class StudyPlanItemModel(Base):
    __tablename__ = "study_plan_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    study_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("study_plans.id"),
        index=True,
    )
    curriculum_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum_items.id"),
        index=True,
    )

    study_plan: Mapped[StudyPlanModel] = relationship(back_populates="items")
    curriculum_item: Mapped[CurriculumItemModel] = relationship(
        back_populates="study_plan_items"
    )


class StudyTaskModel(Base):
    __tablename__ = "study_tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    curriculum_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum_items.id"),
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    curriculum_item: Mapped[CurriculumItemModel] = relationship(
        back_populates="study_tasks"
    )


class StudySessionModel(Base):
    __tablename__ = "study_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    curriculum_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum_items.id"),
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    curriculum_item: Mapped[CurriculumItemModel] = relationship(
        back_populates="study_sessions"
    )


class StudyProgressModel(Base):
    __tablename__ = "study_progress"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    curriculum_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum_items.id"),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String)

    curriculum_item: Mapped[CurriculumItemModel] = relationship(
        back_populates="study_progress"
    )


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NoteModel(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    curriculum_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("curriculum_items.id"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    curriculum_item: Mapped[CurriculumItemModel] = relationship(
        back_populates="notes"
    )


class AssignmentModel(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    due_at: Mapped[datetime] = mapped_column(DateTime)

    course: Mapped[CourseModel] = relationship(back_populates="assignments")


class ExamModel(Base):
    __tablename__ = "exams"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    starts_at: Mapped[datetime] = mapped_column(DateTime)

    course: Mapped[CourseModel] = relationship(back_populates="exams")
