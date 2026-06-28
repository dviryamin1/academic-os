# Academic OS Dogfooding Guide

## Purpose

Use the temporary Streamlit workspace during real study sessions. The objective
is to learn whether the curriculum-item workflow is genuinely useful before a
permanent frontend is designed.

Focus on friction, unclear language, missing context, and unnecessary steps.
Avoid evaluating visual polish as though this were the final interface.

## Start the application

From PowerShell in the repository:

```powershell
uv sync
uv run streamlit run src\academic_os\interfaces\streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501).

## Suggested first-use workflow

1. **Initialize database**
   - Use the sidebar button.
   - Confirm the interface explains the next step.

2. **Import curriculum**
   - Upload `course_catalog_hebrew_values.json`.
   - Keep or change the institution and degree names.
   - Confirm Hebrew text, courses, pages, and hierarchy remain readable.

3. **Select one course**
   - Choose a course you are currently studying.
   - Notice whether the course and item selectors are easy to scan.

4. **Select one curriculum item**
   - Prefer an item you intend to study now.
   - Verify code, title, source, pages, parent, and child items.

5. **Create tasks**
   - Create the reading, summary, practice, and review tasks.
   - Decide whether these tasks describe your real workflow.

6. **Complete a task**
   - Complete the task after doing the corresponding work.
   - Verify the state change is obvious and trustworthy.

7. **Add notes**
   - Capture at least one useful idea in your own words.
   - Reopen or rerun the page and confirm the note remains visible.

8. **Log study time**
   - Log the minutes spent on the item.
   - Confirm the history is understandable without calculation.

9. **Update progress**
   - Set the item to `in progress` or `mastered`.
   - Decide whether the available statuses match your mental model.

## Questions for a real study session

- Could you identify the next useful action without consulting documentation?
- Did the selected curriculum item remain the clear center of the workspace?
- Was any information duplicated or missing?
- Did task completion feel distinct from curriculum progress?
- Were notes and study history useful after returning to the item?
- Did any interaction make you think about database records rather than study?
- What would prevent you from using this again tomorrow?

## Feedback log

Create one copy of this template for every observation:

```markdown
### Observation title

- **Date/time:**
- **Curriculum item:**
- **Action performed:**
- **Expected result:**
- **Actual result:**
- **Confusing part:**
- **Suggested improvement:**
- **Severity:** blocking / frustrating / minor
```

## Session summary

Complete this after each dogfooding session:

```markdown
## Session YYYY-MM-DD

- **Course and item:**
- **Study goal:**
- **Minutes studied:**
- **Tasks completed:**
- **Notes captured:**
- **Final progress status:**
- **Most useful part:**
- **Largest source of friction:**
- **Would I use this tomorrow? Why or why not?**
```

## Improvements to evaluate, not implement yet

- Faster curriculum-item search for courses with many items.
- Direct navigation from parent and child items.
- Editing or deleting accidental notes and study sessions.
- Clearer distinction between task completion and mastery.
- A concise “resume where I stopped” entry point.

These are dogfooding hypotheses, not approved product requirements.

## Initial interface finding

During the first browser-based dogfooding pass, Streamlit tabs returned to the
first tab after widget changes. That made progress and study-duration updates
needlessly repetitive. The temporary GUI now uses a persistent workspace-section
selector instead.
