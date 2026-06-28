# Academic OS — Domain Design Review

**Status:** Post Sprint 1  
**Scope:** Domain design only; no implementation is authorized by this review.

## Executive summary

The Sprint 1 model has the correct dependency direction and a suitably small,
framework-independent domain. `CurriculumItem` is correctly centralized and its
self-reference supports an unlimited hierarchy.

The model should not be persisted unchanged. Four structural decisions should be
resolved first:

1. introduce `AcademicYear` between `Degree` and `Semester`;
2. separate a course catalog definition from its membership in a degree and its
   occurrence in a semester;
3. distinguish `StudyPlan` from an individual planned curriculum item;
4. represent study progress separately from curriculum and task completion.

Other concepts in this review can wait until the sprint that first uses them.
This keeps the model extensible without turning the domain into a speculative
catalog of future features.

## 1. Academic year

**Problem**

`Semester` currently references `Degree` directly. Repeated labels such as
“Semester A” have no explicit academic-year parent, so historical grouping would
depend on interpreting dates or names.

**Why it matters**

Academic years are stable institutional concepts, not presentation-only groups.
They provide an unambiguous boundary for transcripts, plans, course offerings,
and historical reporting. Deriving them from semester dates is unreliable
because academic years can cross calendar years and institutions use different
calendars.

**Recommendation**

Add an `AcademicYear` entity between `Degree` and `Semester`. It should have its
own identity, a human-readable label, and explicit date boundaries. `Semester`
should reference `AcademicYear`; the degree relationship is then obtained
through that parent.

A simpler alternative is an `academic_year` string on `Semester`. That avoids an
entity but duplicates labels and boundaries and gives other concepts no stable
year identifier. It is acceptable only for a reporting field, not for this
long-lived domain.

**Timing**

Address before persistence. This changes the ownership and foreign-key shape of
`Semester`, making later migration unnecessarily expensive.

## 2. Course boundaries and metadata

**Problem**

`Course` currently belongs directly to one `Degree`. This treats a course catalog
definition, its inclusion in a degree, and its delivery in a particular semester
as the same concept. The suggested metadata also mixes those concerns.

**Why it matters**

One course may be shared by multiple degrees, its credit value may differ by
curriculum version, and its language or teaching unit may vary by offering.
Putting all metadata on `Course` creates temporal ambiguity and duplicated course
records.

**Recommendation**

Treat `Course` as the stable catalog definition. Keep:

- `course_code` (the existing `code` field expresses this);
- `title`;
- an institutional/catalog owner once institution modeling is introduced.

Place other data according to its meaning:

- **Credits:** put on the degree–course relationship if credits can vary by
  program or curriculum version; otherwise use a small credit value on the
  catalog course. Do not assume they are universally invariant.
- **Faculty:** model later as an owning academic unit only if the application
  needs organizational reporting. It should not be free text duplicated across
  courses.
- **Institution:** do not duplicate it on both `Degree` and `Course`. A future
  `Institution` identity should own catalog courses and degrees.
- **Language:** place on a course offering when it describes a delivered class;
  use a course default only if the catalog guarantees it.
- **Semester type:** do not place it on `Course`; it belongs to `Semester` or a
  course offering.

Introduce an explicit degree–course association when shared courses or
degree-specific rules are supported. Introduce `CourseOffering` only when the
system must represent a course delivered in a particular semester. Neither is a
replacement for `CurriculumItem`, which remains the source of course content.

**Timing**

Resolve Course ownership and degree membership before persistence. Add optional
organizational and delivery metadata only in the sprint that needs it.

## 3. Study task type

**Problem**

`StudyTask.title` is free text, so the domain cannot reliably distinguish
reading, summarizing, practice, review, and self-testing.

**Why it matters**

Task categories will drive consistent workflow generation, progress summaries,
and later planning policies. Inferring a category from a title is brittle and
language-dependent.

**Recommendation**

Add a `task_type` represented by a small value object with a stable code. Define
an initial canonical vocabulary such as `reading`, `summary`, `practice`,
`review`, and `self_test`.

The alternatives have these tradeoffs:

- A closed enum is simple and type-safe but makes every new category a code and
  data migration.
- A value object preserves type safety and normalization while allowing the
  accepted vocabulary to evolve deliberately.
- A separate entity is justified only if users can configure task types or task
  types acquire behavior and metadata. That complexity is not currently needed.

The title should remain because it describes the particular task; type and title
serve different purposes.

**Timing**

Define before persisting or generating study tasks. No implementation is needed
until the task workflow sprint.

## 4. Event planning impact

**Problem**

`Event` records time but cannot state whether that time constrains study
availability. Treating every event as unavailable time would also be incorrect.

**Why it matters**

Planning must distinguish informational calendar entries from actual capacity
constraints. A title such as “Hospital visit” is not a safe basis for scheduling
decisions.

**Recommendation**

Keep `Event` independent and give it optional, explicit planning impact in the
planning domain. Prefer a `PlanningImpact` value object over loosely related
fields. It can eventually express modes such as no impact, unavailable, or
reduced availability, with a quantitative modifier only if planning requirements
prove one is necessary.

`event_type` is useful for categorization but must not imply planning impact:
two events of the same type may affect availability differently. Avoid a generic
`availability_modifier` until its unit and semantics are defined.

**Timing**

Future planning sprint. It is not required before basic persistence because the
current event data can be extended without changing its identity or ownership.

## 5. Study resource

**Problem**

There is no first-class representation for the materials used to study a
`CurriculumItem`. The existing `source` field is insufficient for PDFs, videos,
articles, presentations, practice files, and external links with their own
identity and metadata.

**Why it matters**

Resources can be reused across multiple curriculum items, updated independently,
and referenced by tasks or notes. Encoding them as source strings would duplicate
data and blur curriculum structure with learning material.

**Recommendation**

Introduce `StudyResource` as a separate entity. It should describe a resource,
not store curriculum content or binary files directly. Its eventual minimum
shape should be driven by supported resource adapters, but identity, title,
resource kind, and an external/storage reference are likely core.

Use an explicit many-to-many relationship with `CurriculumItem`: one resource
may support several items, and one item may use several resources. Relationship
metadata such as purpose or ordering belongs on the association only when a real
use case requires it.

`CourseMaterial` should not be a second competing entity. It can be a resource
role or a course-level association if course-wide materials need representation.

**Timing**

Design before resource persistence or import. It does not block persistence of
the existing core entities if the next sprint excludes resources.

## 6. Curriculum progress and status

**Problem**

Task completion is currently the only available progress signal. Curriculum
mastery is not equivalent to completing one task, and progress does not belong
to the immutable curriculum definition.

**Why it matters**

Curriculum, plan, activity, and progress change at different rates. Storing
status on `CurriculumItem` would contaminate reusable curriculum data; deriving
all progress from tasks would prevent deliberate mastery states and make changes
to workflow definitions rewrite historical meaning.

**Recommendation**

Introduce a separate `StudyProgress` entity keyed to `CurriculumItem` and to the
relevant learner or degree context when multi-profile support is introduced.
Represent its state with a value object or controlled state model. The exact
states should be established from real workflows, but `not_started`,
`in_progress`, and `mastered` illustrate the distinction.

Task completion and study sessions should be evidence that may inform progress;
they should not be the progress record itself. Any automatic transition or
mastery calculation is later business logic.

**Timing**

Decide the entity boundary before persistence because Study Progress is a core
concept in the product vision. Implement it only in the sprint that introduces
progress tracking.

## 7. Curriculum item type

**Problem**

The raw string is extensible but permits spelling, casing, and localization
variants to become different domain values. A closed enum avoids that but cannot
accommodate institution-specific item types without code changes.

**Why it matters**

Item type affects navigation, display, import mapping, and potentially workflow
defaults. Inconsistent values would spread format-specific cleanup across the
application.

**Recommendation**

Replace the raw domain string eventually with a `CurriculumItemType` value
object whose persisted representation remains a stable string code. Provide
canonical codes for common types while allowing deliberate extension by import
adapters or configuration.

Tradeoffs:

- **String:** easiest to import and extend, weakest domain consistency.
- **Enum:** strongest closed vocabulary, poor fit for unknown institutions.
- **Value object:** normalization and domain meaning without permanently closing
  the vocabulary; slightly more code.

Do not localize the stored code. Display labels belong to interfaces.

**Timing**

Address before curriculum persistence or concrete import implementation so
stored values begin with stable semantics.

## 8. Additional core-domain findings

### 8.1 Study plan aggregate and entries

**Problem**

The current `StudyPlan` contains one `curriculum_item_id`, so each row is
effectively a planned-item entry rather than an identifiable semester plan.

**Why it matters**

A plan needs a stable identity and lifecycle independent of its entries. Without
that distinction, plan-level metadata, revisions, and constraints would have to
be repeated on every item.

**Recommendation**

Model `StudyPlan` as the semester-level aggregate and represent its relationship
to curriculum items through `StudyPlanItem` (or an equivalently named
association). Do not put copied curriculum titles or hierarchy data on entries.

**Timing**

Address before persistence. This is a semantic correction to an existing core
entity, not a future feature.

### 8.2 Course offering

**Problem**

The current model cannot distinguish a stable course from its occurrence in a
specific semester.

**Why it matters**

Assignments, exams, language, instructors, and enrollment-specific dates
normally belong to an occurrence, while curriculum content belongs to the
course. Repeated course instances would otherwise overwrite history.

**Recommendation**

Introduce `CourseOffering` when semester-specific course delivery enters scope.
It should reference both `Course` and `Semester`. At that point, evaluate whether
`Assignment` and `Exam` should reference the offering rather than only the
catalog course.

**Timing**

Finalize the boundary before persisting semester-specific assessments. The
entity itself can wait if Sprint 2 persists catalog data only.

### 8.3 Assessment scope

**Problem**

`Exam` and `Assignment` reference a course but cannot identify which curriculum
items they assess.

**Why it matters**

Assessment scope is necessary for targeted preparation and progress analysis,
but duplicating chapter names on an assessment would violate the curriculum
reference rule.

**Recommendation**

Represent scope through associations from an assessment to
`CurriculumItem`. Do not create a separate `ExamScope` aggregate unless scope
later acquires its own lifecycle or rules.

**Timing**

Future assessment-planning sprint.

## 9. Concepts intentionally deferred

- **Flashcard:** a useful learning artifact, but not foundational until active
  recall workflows are in scope.
- **Quiz:** could be a task, resource, or assessment depending on requirements;
  introducing it now would prematurely select one meaning.
- **LearningObjective:** potentially core to mastery, but only after objective-
  based curricula or outcome tracking is required.
- **CourseMaterial:** should initially be modeled through `StudyResource` rather
  than as a parallel hierarchy.

## Recommended decision order

Before any persistence schema is created:

1. `Degree` → `AcademicYear` → `Semester`;
2. catalog `Course` versus degree membership;
3. `StudyPlan` versus `StudyPlanItem`;
4. separate `StudyProgress`;
5. value-object boundaries for curriculum item type and task type.

`CourseOffering`, `StudyResource`, event planning impact, and assessment scope
should be introduced only with the first sprint that exercises those concepts.

