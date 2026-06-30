from dataclasses import dataclass
from uuid import UUID

from academic_os.domain import CurriculumItem


@dataclass(frozen=True, slots=True)
class NavigationEntry:
    item: CurriculumItem
    depth: int


def flatten_hierarchy(
    items: list[CurriculumItem],
) -> tuple[NavigationEntry, ...]:
    """Flatten an arbitrary-depth curriculum tree in stable display order."""

    items_by_id = {item.id: item for item in items}
    children_by_parent: dict[UUID | None, list[CurriculumItem]] = {}
    for item in items:
        parent_id = (
            item.parent_id if item.parent_id in items_by_id else None
        )
        children_by_parent.setdefault(parent_id, []).append(item)
    for children in children_by_parent.values():
        children.sort(key=_item_order_key)

    entries: list[NavigationEntry] = []
    visited: set[UUID] = set()

    def append_branch(item: CurriculumItem, depth: int) -> None:
        if item.id in visited:
            return
        visited.add(item.id)
        entries.append(NavigationEntry(item=item, depth=depth))
        for child in children_by_parent.get(item.id, []):
            append_branch(child, depth + 1)

    for root in children_by_parent.get(None, []):
        append_branch(root, 0)
    for item in sorted(items, key=_item_order_key):
        if item.id not in visited:
            append_branch(item, 0)
    return tuple(entries)


def filter_navigation_entries(
    entries: tuple[NavigationEntry, ...],
    query: str,
) -> tuple[NavigationEntry, ...]:
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return entries
    return tuple(
        entry
        for entry in entries
        if normalized_query
        in " ".join(
            (
                entry.item.code,
                entry.item.title,
                entry.item.pages or "",
            )
        ).casefold()
    )


def preserved_item_code(
    entries: tuple[NavigationEntry, ...],
    selected_code: str | None,
) -> str | None:
    """Keep a valid selection across reruns, otherwise select the first item."""

    if not entries:
        return None
    if selected_code is not None and any(
        entry.item.code == selected_code for entry in entries
    ):
        return selected_code
    return entries[0].item.code


def _item_order_key(item: CurriculumItem) -> tuple[int, str]:
    return item.order, item.code.casefold()
