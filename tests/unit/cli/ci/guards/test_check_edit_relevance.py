"""Tests for check_edit_relevance guard."""

from agentic_devtools.cli.ci.guards import check_edit_relevance
from agentic_devtools.cli.ci.models import EventPayload


class TestCheckEditRelevance:
    """Tests for the edit-relevance preflight guard."""

    def test_non_edited_action_passes_through(self) -> None:
        """Non-edited events always pass through regardless of field values."""
        for action in ("opened", "synchronize", "labeled", "ready_for_review"):
            event = EventPayload(action=action, pr_number=1)
            should_skip, reason = check_edit_relevance(event)
            assert should_skip is False
            assert reason == ""

    def test_edited_unknown_metadata_passes_through(self) -> None:
        """Edited event without reliable change metadata fails open."""
        event = EventPayload(action="edited", edit_changes_known=False, pr_number=1)
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is False
        assert reason == ""

    def test_title_change_proceeds(self) -> None:
        """Edited event with title change should proceed."""
        event = EventPayload(
            action="edited",
            edit_changes_known=True,
            title_changed=True,
            pr_number=1,
        )
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is False
        assert reason == ""

    def test_base_change_proceeds(self) -> None:
        """Edited event with base branch change should proceed."""
        event = EventPayload(
            action="edited",
            edit_changes_known=True,
            base_changed=True,
            pr_number=1,
        )
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is False
        assert reason == ""

    def test_title_and_body_change_proceeds(self) -> None:
        """Edited event with both title and body change should proceed."""
        event = EventPayload(
            action="edited",
            edit_changes_known=True,
            title_changed=True,
            body_changed=True,
            pr_number=1,
        )
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is False
        assert reason == ""

    def test_body_only_skips(self) -> None:
        """Edited event with only body change should skip."""
        event = EventPayload(
            action="edited",
            edit_changes_known=True,
            body_changed=True,
            title_changed=False,
            base_changed=False,
            pr_number=42,
        )
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is True
        assert "title" in reason
        assert "base" in reason

    def test_empty_changes_dict_skips(self) -> None:
        """Edited event with known changes but nothing relevant should skip."""
        event = EventPayload(
            action="edited",
            edit_changes_known=True,
            title_changed=False,
            body_changed=False,
            base_changed=False,
            pr_number=1,
        )
        should_skip, reason = check_edit_relevance(event)
        assert should_skip is True
        assert reason != ""
