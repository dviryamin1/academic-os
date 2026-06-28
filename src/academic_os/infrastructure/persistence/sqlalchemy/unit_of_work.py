from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from academic_os.infrastructure.persistence.sqlalchemy.database import SessionFactory
from academic_os.infrastructure.persistence.sqlalchemy.mappers import (
    ACADEMIC_YEAR_MAPPER,
    ASSIGNMENT_MAPPER,
    COURSE_MAPPER,
    CURRICULUM_ITEM_MAPPER,
    DEGREE_COURSE_MAPPER,
    DEGREE_MAPPER,
    EVENT_MAPPER,
    EXAM_MAPPER,
    INSTITUTION_MAPPER,
    NOTE_MAPPER,
    SEMESTER_MAPPER,
    STUDY_PLAN_ITEM_MAPPER,
    STUDY_PLAN_MAPPER,
    STUDY_PROGRESS_MAPPER,
    STUDY_SESSION_MAPPER,
    STUDY_TASK_MAPPER,
)
from academic_os.infrastructure.persistence.sqlalchemy.repositories import (
    SqlAlchemyRepository,
)


class SqlAlchemyUnitOfWork:
    """One SQLAlchemy session and transaction with domain repositories."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of Work is already active")

        session = self._session_factory()
        session.begin()
        self._session = session

        self.institutions = SqlAlchemyRepository(session, INSTITUTION_MAPPER)
        self.degrees = SqlAlchemyRepository(session, DEGREE_MAPPER)
        self.academic_years = SqlAlchemyRepository(session, ACADEMIC_YEAR_MAPPER)
        self.semesters = SqlAlchemyRepository(session, SEMESTER_MAPPER)
        self.courses = SqlAlchemyRepository(session, COURSE_MAPPER)
        self.degree_courses = SqlAlchemyRepository(session, DEGREE_COURSE_MAPPER)
        self.curriculum_items = SqlAlchemyRepository(
            session,
            CURRICULUM_ITEM_MAPPER,
        )
        self.study_plans = SqlAlchemyRepository(session, STUDY_PLAN_MAPPER)
        self.study_plan_items = SqlAlchemyRepository(
            session,
            STUDY_PLAN_ITEM_MAPPER,
        )
        self.study_tasks = SqlAlchemyRepository(session, STUDY_TASK_MAPPER)
        self.study_sessions = SqlAlchemyRepository(session, STUDY_SESSION_MAPPER)
        self.study_progress = SqlAlchemyRepository(
            session,
            STUDY_PROGRESS_MAPPER,
        )
        self.events = SqlAlchemyRepository(session, EVENT_MAPPER)
        self.notes = SqlAlchemyRepository(session, NOTE_MAPPER)
        self.assignments = SqlAlchemyRepository(session, ASSIGNMENT_MAPPER)
        self.exams = SqlAlchemyRepository(session, EXAM_MAPPER)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if self._session.in_transaction():
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active")
        return self._session

