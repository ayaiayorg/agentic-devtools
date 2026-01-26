"""
Checklist management for workflow implementation steps.

This module provides functions to manage implementation checklists:
- Initialize checklist from Jira acceptance criteria
- Update checklist items (add/remove/edit)
- Mark items as completed
- Check if all items are complete
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...state import get_workflow_state, set_workflow_state


@dataclass
class ChecklistItem:
    """A single checklist item."""

    id: int
    text: str
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChecklistItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            text=data["text"],
            completed=data.get("completed", False),
        )


@dataclass
class Checklist:
    """Implementation checklist with items and metadata."""

    items: List[ChecklistItem] = field(default_factory=list)
    modified_by_agent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "items": [item.to_dict() for item in self.items],
            "modified_by_agent": self.modified_by_agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checklist":
        """Create from dictionary."""
        items = [ChecklistItem.from_dict(item) for item in data.get("items", [])]
        return cls(
            items=items,
            modified_by_agent=data.get("modified_by_agent", False),
        )

    def get_item(self, item_id: int) -> Optional[ChecklistItem]:
        """Get item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def mark_completed(self, item_ids: List[int]) -> List[int]:
        """
        Mark items as completed.

        Args:
            item_ids: List of item IDs to mark complete

        Returns:
            List of IDs that were successfully marked (existed and weren't already complete)
        """
        marked = []
        for item_id in item_ids:
            item = self.get_item(item_id)
            if item and not item.completed:
                item.completed = True
                marked.append(item_id)
        return marked

    def all_complete(self) -> bool:
        """Check if all items are complete."""
        return len(self.items) > 0 and all(item.completed for item in self.items)

    def completion_status(self) -> tuple[int, int]:
        """
        Get completion status.

        Returns:
            Tuple of (completed_count, total_count)
        """
        completed = sum(1 for item in self.items if item.completed)
        return completed, len(self.items)

    def add_item(self, text: str) -> ChecklistItem:
        """Add a new item to the checklist."""
        new_id = max((item.id for item in self.items), default=0) + 1
        item = ChecklistItem(id=new_id, text=text)
        self.items.append(item)
        self.modified_by_agent = True
        return item

    def remove_item(self, item_id: int) -> bool:
        """
        Remove an item from the checklist.

        Returns:
            True if item was found and removed
        """
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                self.modified_by_agent = True
                return True
        return False

    def update_item(self, item_id: int, new_text: str) -> bool:
        """
        Update an item's text.

        Returns:
            True if item was found and updated
        """
        item = self.get_item(item_id)
        if item:
            item.text = new_text
            self.modified_by_agent = True
            return True
        return False

    def render_markdown(self) -> str:
        """Render checklist as markdown with checkboxes."""
        lines = []
        for item in self.items:
            checkbox = "✅" if item.completed else "⬜"
            lines.append(f"{checkbox} {item.id}. {item.text}")
        return "\n".join(lines)

    def render_plain(self) -> str:
        """Render checklist as plain text with status indicators."""
        lines = []
        for item in self.items:
            status = "[x]" if item.completed else "[ ]"
            lines.append(f"{status} {item.id}. {item.text}")
        return "\n".join(lines)


def get_checklist() -> Optional[Checklist]:
    """
    Get the current checklist from workflow state.

    Returns:
        Checklist object or None if no checklist exists
    """
    workflow = get_workflow_state()
    if not workflow:
        return None

    context = workflow.get("context", {})
    checklist_data = context.get("checklist")
    if not checklist_data:
        return None

    return Checklist.from_dict(checklist_data)


def save_checklist(checklist: Checklist) -> None:
    """
    Save the checklist to workflow state.

    Args:
        checklist: The checklist to save
    """
    workflow = get_workflow_state()
    if not workflow:
        raise ValueError("No active workflow to save checklist to")

    context = workflow.get("context", {})
    context["checklist"] = checklist.to_dict()

    set_workflow_state(
        name=workflow["active"],
        status=workflow.get("status", "in-progress"),
        step=workflow.get("step"),
        context=context,
    )


def initialize_checklist(items: List[str]) -> Checklist:
    """
    Initialize a new checklist with the given items.

    Args:
        items: List of item texts

    Returns:
        New Checklist object (not yet saved to state)
    """
    checklist_items = [ChecklistItem(id=i + 1, text=text) for i, text in enumerate(items)]
    return Checklist(items=checklist_items, modified_by_agent=False)


def mark_items_completed(item_ids: List[int]) -> tuple[Checklist, List[int]]:
    """
    Mark items as completed in the current checklist.

    Args:
        item_ids: List of item IDs to mark complete

    Returns:
        Tuple of (updated checklist, list of IDs that were marked)

    Raises:
        ValueError: If no checklist exists
    """
    checklist = get_checklist()
    if not checklist:
        raise ValueError("No checklist exists in current workflow")

    marked = checklist.mark_completed(item_ids)
    save_checklist(checklist)

    return checklist, marked


def parse_completed_items_arg(arg: str) -> List[int]:
    """
    Parse the --completed argument value into a list of item IDs.

    Accepts formats:
    - "1,2,3" (comma-separated)
    - "1 2 3" (space-separated)
    - "1, 2, 3" (comma with spaces)
    - "1-3" (range)

    Args:
        arg: The argument string

    Returns:
        List of item IDs
    """
    ids = []
    # Split by comma or space
    parts = arg.replace(",", " ").split()

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check for range (e.g., "1-3")
        if "-" in part and not part.startswith("-"):
            try:
                start, end = part.split("-", 1)
                ids.extend(range(int(start), int(end) + 1))
            except ValueError:
                # Not a valid range, try as single number
                try:
                    ids.append(int(part))
                except ValueError:
                    pass
        else:
            try:
                ids.append(int(part))
            except ValueError:
                pass

    return sorted(set(ids))  # Deduplicate and sort
