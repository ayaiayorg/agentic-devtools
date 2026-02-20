"""
Tests for Jira update_commands module.

Tests for agdt-update-jira-issue command and payload building.
"""

from agdt_ai_helpers.cli.jira.update_commands import _build_update_payload


class TestBuildUpdatePayload:
    """Tests for _build_update_payload function."""

    def test_empty_payload(self):
        """Test building empty payload when no fields provided."""
        payload = _build_update_payload()
        assert payload == {}

    def test_summary_only(self):
        """Test payload with only summary."""
        payload = _build_update_payload(summary="New Summary")
        assert payload == {"fields": {"summary": "New Summary"}}

    def test_description_only(self):
        """Test payload with only description."""
        payload = _build_update_payload(description="New description text")
        assert payload == {"fields": {"description": "New description text"}}

    def test_assignee_set(self):
        """Test payload with assignee."""
        payload = _build_update_payload(assignee="AMARSNIK")
        assert payload == {"fields": {"assignee": {"name": "AMARSNIK"}}}

    def test_assignee_unset(self):
        """Test payload with empty assignee (unassign)."""
        payload = _build_update_payload(assignee="")
        assert payload == {"fields": {"assignee": None}}

    def test_priority(self):
        """Test payload with priority."""
        payload = _build_update_payload(priority="High")
        assert payload == {"fields": {"priority": {"name": "High"}}}

    def test_labels_replace(self):
        """Test payload with labels replacement."""
        payload = _build_update_payload(labels=["label1", "label2"])
        assert payload == {"fields": {"labels": ["label1", "label2"]}}

    def test_labels_add(self):
        """Test payload with labels to add."""
        payload = _build_update_payload(labels_add=["new-label"])
        assert payload == {"update": {"labels": [{"add": "new-label"}]}}

    def test_labels_remove(self):
        """Test payload with labels to remove."""
        payload = _build_update_payload(labels_remove=["old-label"])
        assert payload == {"update": {"labels": [{"remove": "old-label"}]}}

    def test_labels_add_and_remove(self):
        """Test payload with both labels to add and remove."""
        payload = _build_update_payload(labels_add=["new"], labels_remove=["old"])
        expected = {"update": {"labels": [{"add": "new"}, {"remove": "old"}]}}
        assert payload == expected

    def test_labels_replace_takes_precedence(self):
        """Test that labels replacement ignores add/remove."""
        payload = _build_update_payload(
            labels=["complete-replacement"],
            labels_add=["ignored"],
            labels_remove=["also-ignored"],
        )
        # When labels is set, it goes to fields, not update
        assert payload == {"fields": {"labels": ["complete-replacement"]}}
        assert "update" not in payload

    def test_custom_fields(self):
        """Test payload with custom fields."""
        custom = {"customfield_10001": "value1", "customfield_10002": 42}
        payload = _build_update_payload(custom_fields=custom)
        expected = {"fields": {"customfield_10001": "value1", "customfield_10002": 42}}
        assert payload == expected

    def test_multiple_fields(self):
        """Test payload with multiple fields."""
        payload = _build_update_payload(
            summary="Updated",
            description="New desc",
            priority="Medium",
        )
        expected = {
            "fields": {
                "summary": "Updated",
                "description": "New desc",
                "priority": {"name": "Medium"},
            }
        }
        assert payload == expected

    def test_mixed_fields_and_update(self):
        """Test payload with both fields and update operations."""
        payload = _build_update_payload(
            summary="Updated",
            labels_add=["new-label"],
        )
        expected = {
            "fields": {"summary": "Updated"},
            "update": {"labels": [{"add": "new-label"}]},
        }
        assert payload == expected

