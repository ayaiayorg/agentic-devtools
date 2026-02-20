"""
Tests for Jira formatting utilities.
"""


from agdt_ai_helpers.cli import jira


class TestMergeLabels:
    """Tests for merge_labels function."""

    def test_default_labels(self):
        """Test default labels are included."""
        result = jira.merge_labels()
        assert "createdWithDflyAiHelpers" in result
        assert "zuPriorisieren" in result
        assert "createdByAiAgent" in result
        assert "readyForAiAgent" in result

    def test_custom_labels_merged(self):
        """Test custom labels are merged."""
        result = jira.merge_labels(custom_labels=["myLabel"])
        assert "myLabel" in result
        assert "createdWithDflyAiHelpers" in result

    def test_custom_labels_first_after_default(self):
        """Test custom labels appear after the main default."""
        result = jira.merge_labels(custom_labels=["myLabel"])
        assert result.index("createdWithDflyAiHelpers") == 0
        # Custom labels come after the first default
        assert "myLabel" in result

    def test_duplicate_labels_removed(self):
        """Test duplicate labels are removed (case-insensitive)."""
        result = jira.merge_labels(custom_labels=["ZUPRIORISIEREN"])
        count = sum(1 for label in result if label.lower() == "zupriorisieren")
        assert count == 1

    def test_optional_labels_controlled(self):
        """Test optional labels can be controlled."""
        result = jira.merge_labels(
            include_zu_priorisieren=False,
            include_created_by_ai=False,
            include_ready_for_ai=False,
        )
        assert "createdWithDflyAiHelpers" in result
        assert "zuPriorisieren" not in result
        assert "createdByAiAgent" not in result
        assert "readyForAiAgent" not in result

    def test_none_custom_labels(self):
        """Test None custom labels works."""
        result = jira.merge_labels(custom_labels=None)
        assert "createdWithDflyAiHelpers" in result

    def test_empty_custom_label_filtered(self):
        """Test empty strings in custom labels are filtered."""
        result = jira.merge_labels(custom_labels=["valid", "", None])
        assert "valid" in result
        assert "" not in result

    def test_case_insensitive_deduplication(self):
        """Test deduplication is case-insensitive."""
        result = jira.merge_labels(custom_labels=["CreatedWithDflyAiHelpers"])
        count = sum(1 for label in result if label.lower() == "createdwithdflyaihelpers")
        assert count == 1

