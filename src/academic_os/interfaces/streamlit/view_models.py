from dataclasses import dataclass
from datetime import datetime

from academic_os.application.services import (
    NextStudyRecommendation,
    ResumeLearning,
)

OUTDATED_SCHEMA_MESSAGE = (
    "Your database schema is outdated. Use Upgrade database in the sidebar."
)


@dataclass(frozen=True, slots=True)
class ResumeCard:
    item_code: str
    item_title: str
    course_title: str
    pages: str
    activity_at: datetime
    session_minutes: int | None
    open_task_count: int


@dataclass(frozen=True, slots=True)
class RecommendationCard:
    task_title: str
    task_type: str
    item_code: str
    item_title: str
    course_title: str
    pages: str
    reason: str


def resume_card(resume: ResumeLearning) -> ResumeCard:
    return ResumeCard(
        item_code=resume.item.code,
        item_title=resume.item.title,
        course_title=resume.course.title,
        pages=resume.item.pages or "—",
        activity_at=resume.last_activity_at,
        session_minutes=resume.last_session_duration_minutes,
        open_task_count=len(resume.open_tasks),
    )


def recommendation_card(
    recommendation: NextStudyRecommendation,
) -> RecommendationCard:
    return RecommendationCard(
        task_title=recommendation.task.title,
        task_type=recommendation.task.task_type.code,
        item_code=recommendation.item.code,
        item_title=recommendation.item.title,
        course_title=recommendation.course.title,
        pages=recommendation.item.pages or "—",
        reason=recommendation.reason,
    )


def schema_error_message(error: BaseException) -> str | None:
    messages: list[str] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current).casefold())
        current = current.__cause__ or current.__context__

    combined = " ".join(messages)
    outdated_signatures = (
        "no such column",
        "has no column named",
        "undefined column",
        "unknown column",
    )
    if any(signature in combined for signature in outdated_signatures):
        return OUTDATED_SCHEMA_MESSAGE
    return None
