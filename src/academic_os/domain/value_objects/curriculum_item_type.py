from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class CurriculumItemType:
    CHAPTER: ClassVar[str] = "chapter"
    UNIT: ClassVar[str] = "unit"
    SECTION: ClassVar[str] = "section"
    TOPIC: ClassVar[str] = "topic"
    SUBTOPIC: ClassVar[str] = "subtopic"
    ARTICLE: ClassVar[str] = "article"
    APPENDIX: ClassVar[str] = "appendix"

    code: str
