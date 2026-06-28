"""Create the approved Academic OS domain schema.

Revision ID: 0001
Revises:
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
    )
    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_courses_institution_id_institutions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_index(
        op.f("ix_courses_institution_id"),
        "courses",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "degrees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_degrees_institution_id_institutions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degrees")),
    )
    op.create_index(
        op.f("ix_degrees_institution_id"),
        "degrees",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "academic_years",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("degree_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["degree_id"],
            ["degrees.id"],
            name=op.f("fk_academic_years_degree_id_degrees"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_years")),
    )
    op.create_index(
        op.f("ix_academic_years_degree_id"),
        "academic_years",
        ["degree_id"],
        unique=False,
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_assignments_course_id_courses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_index(
        op.f("ix_assignments_course_id"),
        "assignments",
        ["course_id"],
        unique=False,
    )
    op.create_table(
        "curriculum_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_curriculum_items_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["curriculum_items.id"],
            name=op.f("fk_curriculum_items_parent_id_curriculum_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_items")),
    )
    op.create_index(
        op.f("ix_curriculum_items_course_id"),
        "curriculum_items",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curriculum_items_parent_id"),
        "curriculum_items",
        ["parent_id"],
        unique=False,
    )
    op.create_table(
        "degree_courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("degree_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("credits", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_degree_courses_course_id_courses"),
        ),
        sa.ForeignKeyConstraint(
            ["degree_id"],
            ["degrees.id"],
            name=op.f("fk_degree_courses_degree_id_degrees"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degree_courses")),
    )
    op.create_index(
        op.f("ix_degree_courses_course_id"),
        "degree_courses",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_degree_courses_degree_id"),
        "degree_courses",
        ["degree_id"],
        unique=False,
    )
    op.create_table(
        "exams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_exams_course_id_courses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exams")),
    )
    op.create_index(
        op.f("ix_exams_course_id"),
        "exams",
        ["course_id"],
        unique=False,
    )
    op.create_table(
        "semesters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("academic_year_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["academic_year_id"],
            ["academic_years.id"],
            name=op.f("fk_semesters_academic_year_id_academic_years"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semesters")),
    )
    op.create_index(
        op.f("ix_semesters_academic_year_id"),
        "semesters",
        ["academic_year_id"],
        unique=False,
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_item_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_item_id"],
            ["curriculum_items.id"],
            name=op.f("fk_notes_curriculum_item_id_curriculum_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(
        op.f("ix_notes_curriculum_item_id"),
        "notes",
        ["curriculum_item_id"],
        unique=False,
    )
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("semester_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_study_plans_semester_id_semesters"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plans")),
    )
    op.create_index(
        op.f("ix_study_plans_semester_id"),
        "study_plans",
        ["semester_id"],
        unique=False,
    )
    op.create_table(
        "study_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_item_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_item_id"],
            ["curriculum_items.id"],
            name=op.f("fk_study_progress_curriculum_item_id_curriculum_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_progress")),
        sa.UniqueConstraint(
            "curriculum_item_id",
            name=op.f("uq_study_progress_curriculum_item_id"),
        ),
    )
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_item_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["curriculum_item_id"],
            ["curriculum_items.id"],
            name=op.f("fk_study_sessions_curriculum_item_id_curriculum_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_sessions")),
    )
    op.create_index(
        op.f("ix_study_sessions_curriculum_item_id"),
        "study_sessions",
        ["curriculum_item_id"],
        unique=False,
    )
    op.create_table(
        "study_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_item_id", sa.Uuid(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["curriculum_item_id"],
            ["curriculum_items.id"],
            name=op.f("fk_study_tasks_curriculum_item_id_curriculum_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_tasks")),
    )
    op.create_index(
        op.f("ix_study_tasks_curriculum_item_id"),
        "study_tasks",
        ["curriculum_item_id"],
        unique=False,
    )
    op.create_table(
        "study_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("study_plan_id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_item_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_item_id"],
            ["curriculum_items.id"],
            name=op.f(
                "fk_study_plan_items_curriculum_item_id_curriculum_items"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["study_plan_id"],
            ["study_plans.id"],
            name=op.f("fk_study_plan_items_study_plan_id_study_plans"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plan_items")),
    )
    op.create_index(
        op.f("ix_study_plan_items_curriculum_item_id"),
        "study_plan_items",
        ["curriculum_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_study_plan_items_study_plan_id"),
        "study_plan_items",
        ["study_plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_study_plan_items_study_plan_id"),
        table_name="study_plan_items",
    )
    op.drop_index(
        op.f("ix_study_plan_items_curriculum_item_id"),
        table_name="study_plan_items",
    )
    op.drop_table("study_plan_items")
    op.drop_index(
        op.f("ix_study_tasks_curriculum_item_id"),
        table_name="study_tasks",
    )
    op.drop_table("study_tasks")
    op.drop_index(
        op.f("ix_study_sessions_curriculum_item_id"),
        table_name="study_sessions",
    )
    op.drop_table("study_sessions")
    op.drop_table("study_progress")
    op.drop_index(
        op.f("ix_study_plans_semester_id"),
        table_name="study_plans",
    )
    op.drop_table("study_plans")
    op.drop_index(
        op.f("ix_notes_curriculum_item_id"),
        table_name="notes",
    )
    op.drop_table("notes")
    op.drop_index(
        op.f("ix_semesters_academic_year_id"),
        table_name="semesters",
    )
    op.drop_table("semesters")
    op.drop_index(op.f("ix_exams_course_id"), table_name="exams")
    op.drop_table("exams")
    op.drop_index(
        op.f("ix_degree_courses_degree_id"),
        table_name="degree_courses",
    )
    op.drop_index(
        op.f("ix_degree_courses_course_id"),
        table_name="degree_courses",
    )
    op.drop_table("degree_courses")
    op.drop_index(
        op.f("ix_curriculum_items_parent_id"),
        table_name="curriculum_items",
    )
    op.drop_index(
        op.f("ix_curriculum_items_course_id"),
        table_name="curriculum_items",
    )
    op.drop_table("curriculum_items")
    op.drop_index(
        op.f("ix_assignments_course_id"),
        table_name="assignments",
    )
    op.drop_table("assignments")
    op.drop_index(
        op.f("ix_academic_years_degree_id"),
        table_name="academic_years",
    )
    op.drop_table("academic_years")
    op.drop_index(
        op.f("ix_degrees_institution_id"),
        table_name="degrees",
    )
    op.drop_table("degrees")
    op.drop_index(
        op.f("ix_courses_institution_id"),
        table_name="courses",
    )
    op.drop_table("courses")
    op.drop_table("institutions")
    op.drop_table("events")
