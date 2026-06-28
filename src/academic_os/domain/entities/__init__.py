"""Domain entities."""

from academic_os.domain.entities.academic_year import AcademicYear
from academic_os.domain.entities.assignment import Assignment
from academic_os.domain.entities.course import Course
from academic_os.domain.entities.curriculum_item import CurriculumItem
from academic_os.domain.entities.degree import Degree
from academic_os.domain.entities.degree_course import DegreeCourse
from academic_os.domain.entities.event import Event
from academic_os.domain.entities.exam import Exam
from academic_os.domain.entities.institution import Institution
from academic_os.domain.entities.note import Note
from academic_os.domain.entities.semester import Semester
from academic_os.domain.entities.study_plan import StudyPlan
from academic_os.domain.entities.study_plan_item import StudyPlanItem
from academic_os.domain.entities.study_progress import StudyProgress
from academic_os.domain.entities.study_session import StudySession
from academic_os.domain.entities.study_task import StudyTask

__all__ = [
    "AcademicYear",
    "Assignment",
    "Course",
    "CurriculumItem",
    "Degree",
    "DegreeCourse",
    "Event",
    "Exam",
    "Institution",
    "Note",
    "Semester",
    "StudyPlan",
    "StudyPlanItem",
    "StudyProgress",
    "StudySession",
    "StudyTask",
]
