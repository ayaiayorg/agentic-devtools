"""
Tests for Jira formatting utilities.
"""

from unittest.mock import patch

from agdt_ai_helpers.cli import jira


class TestFormatBulletList:
    """Tests for format_bullet_list function."""

    def test_format_bullet_list_empty(self):
        """Test empty list returns empty string."""
        assert jira.format_bullet_list([]) == ""
        assert jira.format_bullet_list(None) == ""

    def test_format_bullet_list_with_placeholder(self):
        """Test empty list with placeholder returns placeholder."""
        result = jira.format_bullet_list([], "No items")
        assert result == "* No items"

    def test_format_bullet_list_none_with_placeholder(self):
        """Test None with placeholder returns placeholder."""
        result = jira.format_bullet_list(None, "No items")
        assert result == "* No items"

    def test_format_bullet_list_simple(self):
        """Test simple list formatting."""
        result = jira.format_bullet_list(["item1", "item2"])
        assert result == "* item1\n* item2"

    def test_format_bullet_list_preserves_existing_bullets(self):
        """Test existing bullets are preserved."""
        result = jira.format_bullet_list(["* item1", "item2"])
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_preserves_headings(self):
        """Test headings are preserved."""
        result = jira.format_bullet_list(["h3. Heading", "item1"])
        assert "h3. Heading" in result
        assert "* item1" in result

    def test_format_bullet_list_preserves_numbered_items(self):
        """Test numbered items are preserved."""
        result = jira.format_bullet_list(["1. First", "item"])
        assert "1. First" in result
        assert "* item" in result

    def test_format_bullet_list_preserves_hash_headings(self):
        """Test # headings are preserved."""
        result = jira.format_bullet_list(["# Heading", "item"])
        assert "# Heading" in result

    def test_format_bullet_list_skips_empty_items(self):
        """Test empty items are skipped."""
        result = jira.format_bullet_list(["item1", "", "  ", "item2"])
        lines = result.split("\n")
        assert len(lines) == 2
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_strips_whitespace(self):
        """Test whitespace is stripped from items."""
        result = jira.format_bullet_list(["  item1  ", "  item2  "])
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_all_empty_with_placeholder(self):
        """Test all empty items with placeholder returns placeholder."""
        result = jira.format_bullet_list(["", "  "], "No items")
        assert result == "* No items"


class TestBuildUserStoryDescription:
    """Tests for build_user_story_description function."""

    def test_basic_user_story(self):
        """Test basic user story format."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="developer", desired_outcome="a feature", benefit="better UX"
            )

        assert "*As a* developer" in result
        assert "*I would like* a feature" in result
        assert "*so that* better UX" in result
        assert "Acceptance Criteria" in result

    def test_user_story_with_acceptance_criteria(self):
        """Test user story with acceptance criteria."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="login",
                benefit="access",
                acceptance_criteria=["AC1", "AC2"],
            )

        assert "* AC1" in result
        assert "* AC2" in result

    def test_user_story_with_additional_info(self):
        """Test user story with additional information."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="feature",
                benefit="value",
                additional_information=["Info1", "Info2"],
            )

        assert "Additional Information" in result
        assert "* Info1" in result
        assert "* Info2" in result

    def test_user_story_with_reviewer(self):
        """Test user story includes reviewer when email available."""
        with patch.dict("os.environ", {"JIRA_EMAIL": "reviewer@test.com"}):
            result = jira.build_user_story_description(role="user", desired_outcome="feature", benefit="value")

        assert "Reviewer" in result
        assert "reviewer@test.com" in result

    def test_user_story_with_username_reviewer(self):
        """Test user story includes reviewer from username."""
        with patch.dict("os.environ", {"JIRA_USERNAME": "testuser"}, clear=True):
            result = jira.build_user_story_description(role="user", desired_outcome="feature", benefit="value")

        assert "Reviewer" in result
        assert "testuser" in result

    def test_user_story_strips_role(self):
        """Test role whitespace is stripped."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(role="  developer  ", desired_outcome="feature", benefit="value")
        assert "*As a* developer," in result

    def test_user_story_no_additional_info_section_when_empty(self):
        """Test no Additional Information section when list is empty."""
        with patch.dict("os.environ", {}, clear=True):
            result = jira.build_user_story_description(
                role="user",
                desired_outcome="feature",
                benefit="value",
                additional_information=[],
            )
        assert "Additional Information" not in result


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
